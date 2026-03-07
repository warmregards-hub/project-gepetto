FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .

# Build for production preview
RUN npm run build

# Expose port
EXPOSE 5173

# Start preview server
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
