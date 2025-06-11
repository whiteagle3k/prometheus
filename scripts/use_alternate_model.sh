#!/bin/bash
# Script to configure Aletheia to use phi-3 as a fallback

echo "🔄 Configuring Aletheia to use phi-3-medium instead of phi-4..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Create a backup of the current identity.json
echo "📦 Creating backup of current identity.json..."
cp entities/aletheia/identity/identity.json entities/aletheia/identity/identity.json.phi4.bak

# Update the identity.json to use phi-3-medium
echo "✏️ Updating identity.json to use phi-3-medium..."
sed -i.bak 's/"local_model_gguf": "models\/phi-4-Q4_K.gguf"/"local_model_gguf": "models\/phi-3-mini-3.8b-q4_k.gguf"/g' entities/aletheia/identity/identity.json

echo "✅ Configuration updated."
echo "🚀 You can now run the API or tests with phi-3-medium." 