import { Router } from "express";
import { OmnichainAdapter } from "../services/blockchain/adapters";
import { authenticate } from "../middleware/auth";
import { requireOrganization } from "../middleware/tenant";

const router = Router();

router.use(authenticate, requireOrganization);

router.get("/status", async (_req, res) => {
  const adapter = new OmnichainAdapter({ name: "omnichain", chain: "omnichain" });
  const healthy = await adapter.healthCheck();
  if (!healthy) {
    return res.status(503).json({ success: false, error: "Omnichain node unreachable" });
  }
  const [blockNumber, chainId, gasPrice] = await Promise.all([
    adapter.getBlockNumber(),
    adapter.getChainId(),
    adapter.getGasPrice(),
  ]);
  res.json({ success: true, data: { blockNumber, chainId, gasPrice } });
});

router.get("/validators", async (req, res) => {
  const epoch = parseInt(req.query.epoch as string) || 0;
  const adapter = new OmnichainAdapter({ name: "omnichain", chain: "omnichain" });
  const validators = await adapter.getValidators(epoch);
  res.json({ success: true, data: validators });
});

router.get("/balance/:address", async (req, res) => {
  const adapter = new OmnichainAdapter({ name: "omnichain", chain: "omnichain" });
  const balance = await adapter.getBalance(req.params.address);
  res.json({ success: true, data: { address: req.params.address, balance } });
});

router.get("/messages/:nonce", async (req, res) => {
  const nonce = parseInt(req.params.nonce) || 0;
  const adapter = new OmnichainAdapter({ name: "omnichain", chain: "omnichain" });
  const status = await adapter.getMessageStatus(nonce);
  res.json({ success: true, data: { nonce, status } });
});

export default router;
