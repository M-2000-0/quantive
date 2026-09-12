# Build the n8n workflow JSON file
$nodes = @()
$connections = @{}

# Helper function to add nodes
function Add-Node {
    param($id, $name, $type, $typeVersion, $position, $parameters, $credentials = $null, $webhookId = $null, $onError = $null)
    
    $node = @{
        id = $id
        name = $name
        type = $type
        typeVersion = $typeVersion
        position = $position
        parameters = $parameters
    }
    
    if ($credentials) { $node.credentials = $credentials }
    if ($webhookId) { $node.webhookId = $webhookId }
    if ($onError) { $node.onError = $onError }
    
    $script:nodes += $node
}

# Helper function to add connections
function Add-Connection {
    param($sourceNode, $outputIndex, $targetNode)
    
    if (-not $script:connections.ContainsKey($sourceNode)) {
        $script:connections[$sourceNode] = @{
            main = @()
        }
    }
    
    $outputCount = $script:connections[$sourceNode].main.Count
    if ($outputIndex -ge $outputCount) {
        for ($i = $outputCount; $i -le $outputIndex; $i++) {
            $script:connections[$sourceNode].main += @()
        }
    }
    
    $script:connections[$sourceNode].main[$outputIndex] += @{
        node = $targetNode
        type = "main"
        index = 0
    }
}

# SECTION 1: Revenue Dashboard
Add-Node "rev-sched" "Revenue Schedule Trigger" "n8n-nodes-base.scheduleTrigger" 1.1 @(0, 0) @{
    rule = @{ interval = @(@{ field = "hours"; hoursInterval = 1 }) }
}

Add-Node "rev-pg-metrics" "Revenue Postgres Metrics" "n8n-nodes-base.postgres" 2.1 @(220, 0) @{
    operation = "executeQuery"
    query = "SELECT DATE_TRUNC('month', created_at) AS month, plan_tier, COUNT(DISTINCT customer_id) AS customer_count, SUM(amount) AS mrr, SUM(amount) * 12 AS arr, AVG(amount) AS arpu, SUM(amount) / COUNT(DISTINCT customer_id) AS ltv FROM subscriptions WHERE status = 'active' AND created_at >= NOW() - INTERVAL '12 months' GROUP BY DATE_TRUNC('month', created_at), plan_tier ORDER BY month DESC, plan_tier;"
    additionalFields = @{}
} @{ postgres = @{ id = "quantive-db"; name = "Quantive Production DB" } }

Add-Node "rev-code" "Revenue Compute Metrics" "n8n-nodes-base.code" 2 @(440, 0) @{
    jsCode = @"
const items = `$input.all();
const now = new Date();
const currentMonth = items.filter(i => { const d = new Date(i.json.month); return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear(); });
const previousMonth = items.filter(i => { const d = new Date(i.json.month); const prev = new Date(now); prev.setMonth(prev.getMonth() - 1); return d.getMonth() === prev.getMonth() && d.getFullYear() === prev.getFullYear(); });
const currentMRR = currentMonth.reduce((sum, i) => sum + (i.json.mrr || 0), 0);
const previousMRR = previousMonth.reduce((sum, i) => sum + (i.json.mrr || 0), 0);
const mrrGrowthRate = previousMRR > 0 ? ((currentMRR - previousMRR) / previousMRR * 100) : 0;
const revenueByTier = {};
currentMonth.forEach(i => { const tier = i.json.plan_tier; if (!revenueByTier[tier]) revenueByTier[tier] = { mrr: 0, arr: 0, customers: 0 }; revenueByTier[tier].mrr += i.json.mrr || 0; revenueByTier[tier].arr += i.json.arr || 0; revenueByTier[tier].customers += i.json.customer_count || 0; });
const forecast = { nextMonth: currentMRR * (1 + mrrGrowthRate / 100), nextQuarter: currentMRR * 3 * Math.pow(1 + mrrGrowthRate / 100, 3), nextYear: currentMRR * 12 * Math.pow(1 + mrrGrowthRate / 100, 12) };
return [{ json: { timestamp: now.toISOString(), mrr: currentMRR, arr: currentMRR * 12, arpu: currentMonth.reduce((sum, i) => sum + (i.json.arpu || 0), 0) / Math.max(currentMonth.length, 1), ltv: currentMonth.reduce((sum, i) => sum + (i.json.ltv || 0), 0) / Math.max(currentMonth.length, 1), mrrGrowthRate, revenueByTier, forecast, totalCustomers: currentMonth.reduce((sum, i) => sum + (i.json.customer_count || 0), 0) } }];
"@
}

Add-Node "rev-http" "Revenue HTTP Post" "n8n-nodes-base.httpRequest" 4.1 @(660, 0) @{
    method = "POST"
    url = "={{ `$env.BACKEND_URL }}/api/analytics/revenue"
    sendHeaders = $true
    headerParameters = @{ parameters = @(@{ name = "Content-Type"; value = "application/json" }, @{ name = "Authorization"; value = "=Bearer {`$env.BACKEND_API_KEY}" }) }
    sendBody = $true
    specifyBody = "json"
    jsonBody = "={{ JSON.stringify(`$json) }}"
    options = @{ retryOnFail = $true; maxTries = 3; timeout = 30000 }
} $null $null "continueRegularOutput"

Add-Node "rev-pg-insert" "Revenue Postgres Insert" "n8n-nodes-base.postgres" 2.1 @(880, 0) @{
    operation = "executeQuery"
    query = "INSERT INTO revenue_dashboard_data (timestamp, mrr, arr, arpu, ltv, mrr_growth_rate, revenue_by_tier, forecast, total_customers) VALUES ('{{ `$json.timestamp }}', {{ `$json.mrr }}, {{ `$json.arr }}, {{ `$json.arpu }}, {{ `$json.ltv }}, {{ `$json.mrrGrowthRate }}, '{{ JSON.stringify(`$json.revenueByTier) }}'::jsonb, '{{ JSON.stringify(`$json.forecast) }}'::jsonb, {{ `$json.totalCustomers }});"
    additionalFields = @{}
} @{ postgres = @{ id = "quantive-db"; name = "Quantive Production DB" } }

Add-Connection "rev-sched" 0 "rev-pg-metrics"
Add-Connection "rev-pg-metrics" 0 "rev-code"
Add-Connection "rev-code" 0 "rev-http"
Add-Connection "rev-http" 0 "rev-pg-insert"

# SECTION 2: MRR Dashboard
Add-Node "mrr-sched" "MRR Schedule Trigger" "n8n-nodes-base.scheduleTrigger" 1.1 @(0, 200) @{
    rule = @{ interval = @(@{ field = "hours"; hoursInterval = 1 }) }
}

Add-Node "mrr-pg" "MRR Postgres Breakdown" "n8n-nodes-base.postgres" 2.1 @(220, 200) @{
    operation = "executeQuery"
    query = "WITH current_mrr AS (SELECT plan_tier, SUM(amount) AS mrr FROM subscriptions WHERE status = 'active' GROUP BY plan_tier), previous_mrr AS (SELECT plan_tier, SUM(amount) AS mrr FROM subscriptions WHERE status = 'active' AND created_at < DATE_TRUNC('month', NOW()) GROUP BY plan_tier), new_mrr AS (SELECT plan_tier, SUM(amount) AS mrr FROM subscriptions WHERE status = 'active' AND created_at >= DATE_TRUNC('month', NOW()) GROUP BY plan_tier), churned_mrr AS (SELECT plan_tier, SUM(amount) AS mrr FROM subscriptions WHERE status = 'cancelled' AND cancelled_at >= DATE_TRUNC('month', NOW()) GROUP BY plan_tier) SELECT c.plan_tier, c.mrr AS current_mrr, COALESCE(p.mrr, 0) AS previous_mrr, COALESCE(n.mrr, 0) AS new_mrr, COALESCE(ch.mrr, 0) AS churned_mrr, COALESCE(p.mrr, 0) - COALESCE(ch.mrr, 0) AS retained_mrr FROM current_mrr c LEFT JOIN previous_mrr p ON c.plan_tier = p.plan_tier LEFT JOIN new_mrr n ON c.plan_tier = n.plan_tier LEFT JOIN churned_mrr ch ON c.plan_tier = ch.plan_tier ORDER BY c.plan_tier;"
    additionalFields = @{}
} @{ postgres = @{ id = "quantive-db"; name = "Quantive Production DB" } }

Add-Node "mrr-code" "MRR Compute Components" "n8n-nodes-base.code" 2 @(440, 200) @{
    jsCode = @"
const items = `$input.all();
const now = new Date();
let totalMRR = 0, totalNewMRR = 0, totalExpansionMRR = 0, totalContractionMRR = 0, totalChurnedMRR = 0;
const mrrByPlan = {};
items.forEach(item => { const d = item.json; const tier = d.plan_tier; totalMRR += d.current_mrr || 0; totalNewMRR += d.new_mrr || 0; totalChurnedMRR += d.churned_mrr || 0; if (!mrrByPlan[tier]) mrrByPlan[tier] = { mrr: 0, previousMrr: 0, newMrr: 0, churnedMrr: 0, netNewMrr: 0 }; mrrByPlan[tier].mrr += d.current_mrr || 0; mrrByPlan[tier].previousMrr += d.previous_mrr || 0; mrrByPlan[tier].newMrr += d.new_mrr || 0; mrrByPlan[tier].churnedMrr += d.churned_mrr || 0; mrrByPlan[tier].netNewMrr = mrrByPlan[tier].newMrr - mrrByPlan[tier].churnedMrr; if (d.current_mrr > (d.previous_mrr || 0)) totalExpansionMRR += d.current_mrr - (d.previous_mrr || 0); else totalContractionMRR += (d.previous_mrr || 0) - d.current_mrr; });
const netNewMRR = totalNewMRR + totalExpansionMRR - totalContractionMRR - totalChurnedMRR;
const previousTotalMRR = items.reduce((sum, i) => sum + (i.json.previous_mrr || 0), 0);
const growthRate = previousTotalMRR > 0 ? ((totalMRR - previousTotalMRR) / previousTotalMRR * 100) : 0;
return [{ json: { timestamp: now.toISOString(), totalMRR, totalNewMRR, totalExpansionMRR, totalContractionMRR, totalChurnedMRR, netNewMRR, growthRate, previousTotalMRR, mrrByPlan, arr: totalMRR * 12 } }];
"@
}

Add-Node "mrr-http" "MRR HTTP Post" "n8n-nodes-base.httpRequest" 4.1 @(660, 200) @{
    method = "POST"
    url = "={{ `$env.BACKEND_URL }}/api/analytics/mrr"
    sendHeaders = $true
    headerParameters = @{ parameters = @(@{ name = "Content-Type"; value = "application/json" }, @{ name = "Authorization"; value = "=Bearer {`$env.BACKEND_API_KEY}" }) }
    sendBody = $true
    specifyBody = "json"
    jsonBody = "={{ JSON.stringify(`$json) }}"
    options = @{ retryOnFail = $true; maxTries = 3; timeout = 30000 }
} $null $null "continueRegularOutput"

Add-Node "mrr-pg-insert" "MRR Postgres Insert" "n8n-nodes-base.postgres" 2.1 @(880, 200) @{
    operation = "executeQuery"
    query = "INSERT INTO mrr_dashboard_data (timestamp, total_mrr, total_new_mrr, total_expansion_mrr, total_contraction_mrr, total_churned_mrr, net_new_mrr, growth_rate, previous_total_mrr, mrr_by_plan, arr) VALUES ('{{ `$json.timestamp }}', {{ `$json.totalMRR }}, {{ `$json.totalNewMRR }}, {{ `$json.totalExpansionMRR }}, {{ `$json.totalContractionMRR }}, {{ `$json.totalChurnedMRR }}, {{ `$json.netNewMRR }}, {{ `$json.growthRate }}, {{ `$json.previousTotalMRR }}, '{{ JSON.stringify(`$json.mrrByPlan) }}'::jsonb, {{ `$json.arr }});"
    additionalFields = @{}
} @{ postgres = @{ id = "quantive-db"; name = "Quantive Production DB" } }

Add-Connection "mrr-sched" 0 "mrr-pg"
Add-Connection "mrr-pg" 0 "mrr-code"
Add-Connection "mrr-code" 0 "mrr-http"
Add-Connection "mrr-http" 0 "mrr-pg-insert"

# Build the workflow JSON
$workflow = @{
    name = "Quantive Management Dashboard & Internal Operations"
    nodes = $nodes
    connections = $connections
    settings = @{ executionOrder = "v1" }
}

$json = $workflow | ConvertTo-Json -Depth 10
$json | Out-File -FilePath "C:\Users\HP\OneDrive\Desktop\Quantive\n8n-workflows\workflows\04-management-internal.json" -Encoding utf8
Write-Output "Workflow file created with $($nodes.Count) nodes"
