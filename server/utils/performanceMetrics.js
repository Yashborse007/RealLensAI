import { AsyncLocalStorage } from "node:async_hooks";
import { performance } from "node:perf_hooks";

export const requestPerformanceContext = new AsyncLocalStorage();

export const recordMongoCommand = (durationMs, context) => {
  if (!context) return;
  context.mongoQueryTimeMs += durationMs;
  context.mongoQueryCount += 1;
};

export const requestPerformanceMiddleware = (_req, res, next) => {
  const context = {
    startedAt: performance.now(),
    mongoQueryTimeMs: 0,
    mongoQueryCount: 0,
  };

  requestPerformanceContext.run(context, () => {
    const writeHead = res.writeHead;
    const end = res.end;
    const setTimingHeaders = () => {
      if (res.headersSent) return;
      const requestTimeMs = performance.now() - context.startedAt;
      res.setHeader("X-Request-Time-Ms", requestTimeMs.toFixed(3));
      res.setHeader(
        "X-Mongo-Query-Time-Ms",
        context.mongoQueryTimeMs.toFixed(3),
      );
      res.setHeader("X-Mongo-Query-Count", String(context.mongoQueryCount));
      res.setHeader(
        "Server-Timing",
        `app;dur=${requestTimeMs.toFixed(3)}, mongo;dur=${context.mongoQueryTimeMs.toFixed(3)}`,
      );
    };

    res.writeHead = function (...args) {
      setTimingHeaders();
      return writeHead.apply(this, args);
    };
    res.end = function (...args) {
      setTimingHeaders();
      return end.apply(this, args);
    };
    next();
  });
};
