# Frontend

React/TypeScript administrator dashboard for the simulated ALPR dynamic toll prototype.

## Local webcam ALPR

The initial UI provides a browser-based local webcam preview. It requests camera permission only when **Start camera** is pressed, samples JPEG frames at the interval returned by the local backend, and stops every media track when **Stop camera** is pressed. Frames are sent only to the configured local FastAPI URL and are not stored by the frontend.

Set `VITE_API_BASE_URL` when the API is not running at `http://127.0.0.1:8000`.
