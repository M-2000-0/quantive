/**
 * Email templates for transactional emails.
 * These are HTML templates that can be sent via any email service.
 * They use inline CSS for maximum email client compatibility.
 */

interface EmailTemplate {
 subject: string;
 html: string;
 text: string;
}

const BASE_STYLES = `
 body { margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
 .container { max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; margin-top: 24px; margin-bottom: 24px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); }
 .header { background: linear-gradient(135deg, #3b82f6, #6366f1); padding: 32px 40px; text-align: center; }
 .header h1 { color: #ffffff; font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -0.02em; }
 .body { padding: 32px 40px; color: #334155; font-size: 14px; line-height: 1.6; }
 .body h2 { color: #0f172a; font-size: 18px; font-weight: 700; margin: 0 0 12px 0; }
 .body p { margin: 0 0 16px 0; }
 .btn { display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #3b82f6, #6366f1); color: #ffffff; font-weight: 600; font-size: 14px; text-decoration: none; border-radius: 12px; margin: 16px 0; }
 .footer { padding: 24px 40px; background: #f8fafc; text-align: center; color: #94a3b8; font-size: 12px; border-top: 1px solid #e2e8f0; }
 .footer a { color: #64748b; text-decoration: none; }
 .code-box { background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-family: 'SF Mono', Consolas, monospace; font-size: 24px; font-weight: 700; text-align: center; color: #1e293b; letter-spacing: 4px; margin: 16px 0; }
 .info-box { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 16px; margin: 16px 0; }
 .warning-box { background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 16px; margin: 16px 0; }
 .success-box { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 16px; margin: 16px 0; }
`;

function wrap(bodyContent: string): string {
 return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="${BASE_STYLES.replace(/\n\s*/g, ' ').trim()}">
 <div class="container">
 <div class="header">
 <h1>Quantive</h1>
 </div>
 <div class="body">
 ${bodyContent}
 </div>
 <div class="footer">
 <p>Quantive — Debt Portfolio Intelligence</p>
 <p style="margin-top:8px">
 <a href="#">Unsubscribe</a> &middot; <a href="#">Privacy Policy</a> &middot; <a href="#">Help Center</a>
 </p>
 </div>
 </div>
</body>
</html>`;
}

// ── Welcome Email ────────────────────────────────────────────────────────────

export function welcomeEmail(name: string, loginUrl: string): EmailTemplate {
 const html = wrap(`
 <h2>Welcome to Quantive, ${escapeHtml(name)}! 🎉</h2>
 <p>Your account is ready. Start optimizing your debt portfolio with AI-powered recommendations.</p>
 <div class="info-box">
 <strong>Quick start:</strong>
 <ol style="margin:8px 0 0 16px; padding:0; font-size:13px">
 <li>Create your first portfolio (import CSV or use demo data)</li>
 <li>Run an optimization with your preferred strategy</li>
 <li>Review AI recommendations in the Advisor tab</li>
 </ol>
 </div>
 <a href="${escapeHtml(loginUrl)}" class="btn">Go to Dashboard</a>
 <p style="font-size:13px; color:#64748b">
 Need help? Reply to this email or visit our <a href="${escapeHtml(loginUrl.replace('/login', '/status'))}" style="color:#3b82f6">documentation</a>.
 </p>
 `);

 return {
 subject: 'Welcome to Quantive — Your debt portfolio platform is ready',
 html,
 text: `Welcome to Quantive, ${name}!\n\nYour account is ready. Start optimizing your debt portfolio.\n\nGo to Dashboard: ${loginUrl}\n\nNeed help? Reply to this email.`,
 };
}

// ── Password Reset ───────────────────────────────────────────────────────────

export function passwordResetEmail(name: string, resetUrl: string): EmailTemplate {
 const html = wrap(`
 <h2>Reset your password</h2>
 <p>Hi ${escapeHtml(name)}, we received a request to reset your password.</p>
 <p>Click the button below to set a new password. This link expires in <strong>1 hour</strong>.</p>
 <a href="${escapeHtml(resetUrl)}" class="btn">Reset Password</a>
 <div class="warning-box">
 <strong>Didn't request this?</strong> Ignore this email and your password will remain unchanged.
 </div>
 <p style="font-size:13px; color:#64748b">
 If the button doesn't work, copy this link:<br>
 <span style="word-break:break-all; color:#3b82f6">${escapeHtml(resetUrl)}</span>
 </p>
 `);

 return {
 subject: 'Reset your Quantive password',
 html,
 text: `Hi ${name},\n\nReset your password: ${resetUrl}\n\nThis link expires in 1 hour.\n\nDidn't request this? Ignore this email.`,
 };
}

// ── Report Ready ─────────────────────────────────────────────────────────────

export function reportReadyEmail(
 name: string,
 reportName: string,
 portfolioName: string,
 downloadUrl: string
): EmailTemplate {
 const html = wrap(`
 <h2>Your report is ready <BarChart3 className="w-4 h-4 inline" /> </h2>
 <p>Hi ${escapeHtml(name)}, your optimization report has been generated.</p>
 <div class="success-box">
 <strong>${escapeHtml(reportName)}</strong><br>
 <span style="font-size:13px; color:#64748b">Portfolio: ${escapeHtml(portfolioName)}</span>
 </div>
 <a href="${escapeHtml(downloadUrl)}" class="btn">Download Report</a>
 <p style="font-size:13px; color:#64748b">
 You can also view this report in your <a href="${escapeHtml(downloadUrl.replace('/reports', '/reports'))}" style="color:#3b82f6">Reports dashboard</a>.
 </p>
 `);

 return {
 subject: `Report ready: ${reportName}`,
 html,
 text: `Hi ${name},\n\nYour report "${reportName}" for portfolio "${portfolioName}" is ready.\n\nDownload: ${downloadUrl}`,
 };
}

// ── Optimization Complete ────────────────────────────────────────────────────

export function optimizationCompleteEmail(
 name: string,
 optimizationName: string,
 costReduction: string,
 strategiesCount: number,
 dashboardUrl: string
): EmailTemplate {
 const html = wrap(`
 <h2>Optimization complete <CheckCircle className="w-4 h-4 inline" /> </h2>
 <p>Hi ${escapeHtml(name)}, your portfolio optimization has finished.</p>
 <div class="success-box">
 <strong>${escapeHtml(optimizationName)}</strong><br>
 <div style="margin-top:8px; font-size:24px; font-weight:700; color:#16a34a">${escapeHtml(costReduction)}</div>
 <span style="font-size:13px; color:#64748b">estimated cost reduction</span><br>
 <span style="font-size:13px; color:#64748b">${strategiesCount} strategies generated</span>
 </div>
 <a href="${escapeHtml(dashboardUrl)}" class="btn">View Results</a>
 `);

 return {
 subject: `Optimization complete: ${optimizationName}`,
 html,
 text: `Hi ${name},\n\nYour optimization "${optimizationName}" is complete.\nEstimated cost reduction: ${costReduction}\n${strategiesCount} strategies generated.\n\nView Results: ${dashboardUrl}`,
 };
}

// ── MFA Code ─────────────────────────────────────────────────────────────────

export function mfaCodeEmail(name: string, code: string): EmailTemplate {
 const html = wrap(`
 <h2>Your verification code</h2>
 <p>Hi ${escapeHtml(name)}, enter this code to sign in:</p>
 <div class="code-box">${escapeHtml(code)}</div>
 <p style="font-size:13px; color:#64748b">
 This code expires in <strong>10 minutes</strong>. If you didn't request this, please ignore this email.
 </p>
 `);

 return {
 subject: `Your Quantive verification code: ${code}`,
 html,
 text: `Hi ${name},\n\nYour verification code: ${code}\n\nExpires in 10 minutes.`,
 };
}

function escapeHtml(str: string): string {
 return str
 .replace(/&/g, '&amp;')
 .replace(/</g, '&lt;')
 .replace(/>/g, '&gt;')
 .replace(/"/g, '&quot;')
 .replace(/'/g, '&#039;');
}
