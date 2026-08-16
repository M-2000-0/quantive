import pino from "pino";
import { config } from "./index";

export const logger = pino({
  level: config.logging.level,
  transport: config.isDev
    ? {
        target: "pino-pretty",
        options: { colorize: true, translateTime: "SYS:standard" },
      }
    : undefined,
  redact: ["req.headers.authorization", "req.headers.cookie"],
});
