# Hermes

Hermes is a full-stack monorepo managed with [Nx](https://nx.dev/). It features a modern React frontend and a robust FastAPI backend.

## 🏗 Project Structure

This workspace contains the following applications:

- **`apps/hermes`**: The frontend application. Built with React, React Router 7, and Vite.
- **`apps/hermes-api`**: The backend API. Built with Python and [FastAPI](https://fastapi.tiangolo.com/), using `uv` for dependency management.
- **`apps/hermes-e2e`**: End-to-end testing suite for the frontend, typically using Playwright.

## 🚀 Getting Started

### Prerequisites

Ensure you have the following installed:
- Node.js (v18+)
- npm, yarn, or pnpm
- Python (v3.9+)
- [uv](https://github.com/astral-sh/uv) (for Python dependency management)

### Installation

Clone the repository and install the dependencies:

```bash
# Install Node.js dependencies
npm install

# The Python dependencies for hermes-api are managed by uv and Nx automatically
```

### Running the Development Servers

You can run the applications locally using Nx CLI.

**Start the Frontend:**
```bash
npx nx serve hermes
```
The frontend should be accessible at `http://localhost:4200` (or another port specified in the console).

**Start the Backend API:**
```bash
npx nx serve hermes-api
```
The FastAPI application will be accessible locally. You can view the interactive API documentation at `http://localhost:8000/docs` (default FastAPI port unless configured otherwise).

## 🧪 Testing and Building

### Running Tests

To execute unit tests for a specific project:
```bash
npx nx test hermes
npx nx test hermes-api
```

To run end-to-end tests for the frontend:
```bash
npx nx e2e hermes-e2e
```

### Building for Production

To create a production bundle for your applications:
```bash
npx nx build hermes
npx nx build hermes-api
```
The build artifacts will be stored in the `dist/` directory at the root of the workspace.

## 🛠 Useful Commands

- `npx nx graph` - Visually explore the workspace dependency graph.
- `npx nx show project hermes` - See all available tasks for the frontend project.
- `npx nx show project hermes-api` - See all available tasks for the backend project.

## 📚 Learn More

- [Nx Documentation](https://nx.dev)
- [React Router Documentation](https://reactrouter.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
