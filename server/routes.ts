import type { Express } from "express";
import { createServer, type Server } from "http";

export function registerRoutes(app: Express): Server {
  const httpServer = createServer(app);
  
  // Proxy API requests to Python backend
  const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
  
  // Proxy all /api requests to Python backend
  app.use('/api', async (req, res) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api${req.path}`, {
        method: req.method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
      });
      
      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error) {
      console.error('Backend proxy error:', error);
      res.status(500).json({ error: 'Backend connection failed' });
    }
  });
  
  return httpServer;
}