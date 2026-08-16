import { Router } from "express";
import { authController } from "../controllers/auth";
import { validate } from "../middleware/validation";
import { loginSchema, registerSchema, refreshSchema } from "../validators/auth";
import { authenticate } from "../middleware/auth";

const router = Router();

router.post("/register", validate(registerSchema), (req, res, next) => authController.register(req, res).catch(next));
router.post("/login", validate(loginSchema), (req, res, next) => authController.login(req, res).catch(next));
router.post("/refresh", validate(refreshSchema), (req, res, next) => authController.refresh(req, res).catch(next));
router.post("/logout", authenticate, (req, res, next) => authController.logout(req, res).catch(next));
router.get("/me", authenticate, (req, res, next) => authController.me(req, res).catch(next));

export default router;
