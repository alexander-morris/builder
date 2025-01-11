# Express Website

A simple website built with Express.js, featuring modern styling and a health check endpoint.

## Features

- Express.js server with static file serving
- Modern, responsive design with CSS variables
- Health check API endpoint
- Automated tests with Jest and Supertest

## Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd express-website
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Development

Start the development server with hot reload:
```bash
npm run dev
```

The server will start at http://localhost:3000

## Testing

Run tests once:
```bash
npm test
```

Run tests in watch mode:
```bash
npm run test:watch
```

## Production

Start the production server:
```bash
npm start
```

## Project Structure

```
.
├── src/
│   ├── server.js          # Express server configuration
│   ├── routes/            # API routes
│   └── public/            # Static files
│       ├── index.html     # Main HTML file
│       ├── css/           # Stylesheets
│       └── js/            # Client-side JavaScript
├── tests/                 # Test files
└── package.json          # Project configuration
```

## API Endpoints

- `GET /api/health` - Check server health status

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 