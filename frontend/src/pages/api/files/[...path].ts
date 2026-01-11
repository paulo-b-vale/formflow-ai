import { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Get the path segments after /api/files/
  const { path } = req.query;
  const pathStr = Array.isArray(path) ? path.join('/') : path;
  
  // Get query parameters and construct URL with them
  const { url } = req;
  let queryString = '';
  if (url) {
    const urlParts = url.split('?');
    if (urlParts.length > 1) {
      queryString = urlParts[1];
    }
  }
  
  // Construct the backend API URL with query parameters
  let backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002'}/files/${pathStr}`;
  if (queryString) {
    backendUrl += `?${queryString}`;
  }
  
  try {
    // Forward the request to the backend, preserving original headers and content type
    const response = await axios({
      method: req.method,
      url: backendUrl,
      data: req.body,
      headers: {
        ...req.headers,
        // Remove host header to prevent issues
        host: undefined,
        'content-length': undefined, // Let axios calculate this
      },
      validateStatus: () => true, // Don't throw on 4xx/5xx status codes
    });

    // Set the response headers from the backend response
    Object.entries(response.headers).forEach(([key, value]) => {
      if (value !== undefined) {
        res.setHeader(key, value);
      }
    });

    // Return the response from the backend
    res.status(response.status).send(response.data);
  } catch (error) {
    // Handle errors
    if (axios.isAxiosError(error)) {
      // Set response headers if available
      if (error.response?.headers) {
        Object.entries(error.response.headers).forEach(([key, value]) => {
          if (value !== undefined) {
            res.setHeader(key, value);
          }
        });
      }
      
      res.status(error.response?.status || 500).json({
        error: {
          type: 'proxy_error',
          message: error.message,
        },
      });
    } else {
      res.status(500).json({
        error: {
          type: 'unknown_error',
          message: 'An unexpected error occurred',
        },
      });
    }
  }
}

// Config to allow body parsing
export const config = {
  api: {
    bodyParser: {
      sizeLimit: '1mb',
    },
  },
};