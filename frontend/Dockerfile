# Use Node.js 20 alpine
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package configurations
COPY package*.json ./

# Install npm dependencies
RUN npm install

# Copy source code
COPY . .

# Build production bundle
RUN npm run build

# Expose port
EXPOSE 3000

# Start production server
CMD ["npm", "run", "start"]
