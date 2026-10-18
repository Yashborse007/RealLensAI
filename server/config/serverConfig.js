export const DEFAULT_BACKEND_PORT = 5000;
export const AI_SERVICE_PORT = 8000;

export const getBackendPort = (configuredPort = process.env.PORT) => {
  const parsedPort = Number.parseInt(configuredPort, 10);
  if (!Number.isInteger(parsedPort) || parsedPort < 1 || parsedPort > 65535) {
    return DEFAULT_BACKEND_PORT;
  }

  return parsedPort === AI_SERVICE_PORT ? DEFAULT_BACKEND_PORT : parsedPort;
};
