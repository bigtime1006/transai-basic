FROM node:18

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies first
RUN npm install

# Copy all files
COPY . .

# Set environment variables for the frontend
ENV VITE_API_BASE_URL=http://host.docker.internal:8000

# Set correct permissions for the entrypoint script
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 5173

ENTRYPOINT ["./docker-entrypoint.sh"]