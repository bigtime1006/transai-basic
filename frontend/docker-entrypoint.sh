#!/bin/bash

# Install dependencies if node_modules doesn't exist or is empty
if [ ! -d "node_modules" ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Fix permissions for npm binaries
chmod +x node_modules/.bin/* 2>/dev/null || true

# Run the development server using npx to ensure vite is found
npx vite --host 0.0.0.0