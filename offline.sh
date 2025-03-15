#!/bin/bash
# Script to fix Font Awesome for offline use

echo "Fixing Font Awesome for offline use..."

# 1. Create directories if they don't exist
mkdir -p app/static/lib/fontawesome/webfonts

# 2. Check if we need to download Font Awesome
if [ ! -f "fontawesome-free-6.4.0-web.zip" ]; then
  echo "Downloading Font Awesome..."
  wget https://use.fontawesome.com/releases/v6.4.0/fontawesome-free-6.4.0-web.zip
else
  echo "Using existing Font Awesome download..."
fi

# 3. Extract and copy files
echo "Extracting and setting up Font Awesome files..."
unzip -q fontawesome-free-6.4.0-web.zip

# 4. Copy web fonts
echo "Copying web fonts..."
cp fontawesome-free-6.4.0-web/webfonts/*.ttf app/static/lib/fontawesome/webfonts/
cp fontawesome-free-6.4.0-web/webfonts/*.woff2 app/static/lib/fontawesome/webfonts/

# 5. Copy and modify CSS - Fix path references
echo "Setting up CSS with correct paths..."
cp fontawesome-free-6.4.0-web/css/all.min.css app/static/lib/fontawesome/

# 6. Clean up
echo "Cleaning up..."
rm -rf fontawesome-free-6.4.0-web

# 7. Testing for font file existence
echo "Verifying files..."
if [ -f "app/static/lib/fontawesome/webfonts/fa-solid-900.woff2" ]; then
  echo "✓ Font files correctly installed"
else
  echo "✗ Error: Font files not found!"
fi

# 8. Create simplified local-fontawesome.css file with hardcoded paths
echo "Creating simplified FontAwesome CSS..."
cat > app/static/lib/fontawesome/local-fontawesome.css << 'EOF'
/* Simplified FontAwesome CSS with local paths */
@font-face {
  font-family: 'FontAwesome';
  font-style: normal;
  font-weight: 900;
  src: url("webfonts/fa-solid-900.woff2") format("woff2"),
       url("webfonts/fa-solid-900.ttf") format("truetype");
}

@font-face {
  font-family: 'FontAwesome';
  font-style: normal;
  font-weight: 400;
  src: url("webfonts/fa-regular-400.woff2") format("woff2"),
       url("webfonts/fa-regular-400.ttf") format("truetype");
}

@font-face {
  font-family: 'FontAwesome Brands';
  font-style: normal;
  font-weight: 400;
  src: url("webfonts/fa-brands-400.woff2") format("woff2"),
       url("webfonts/fa-brands-400.ttf") format("truetype");
}

.fas,
.fa-solid {
  font-family: 'FontAwesome';
  font-weight: 900;
}

.far,
.fa-regular {
  font-family: 'FontAwesome';
  font-weight: 400;
}

.fab,
.fa-brands {
  font-family: 'FontAwesome Brands';
  font-weight: 400;
}

/* Common base styles for all icons */
.fas, .far, .fab {
  -moz-osx-font-smoothing: grayscale;
  -webkit-font-smoothing: antialiased;
  display: inline-block;
  font-style: normal;
  font-variant: normal;
  text-rendering: auto;
  line-height: 1;
}

/* Key icons used in the application */
.fa-folder:before { content: "\f07b"; }
.fa-folder-plus:before { content: "\f65e"; }
.fa-moon:before { content: "\f186"; }
.fa-sun:before { content: "\f185"; }
.fa-caret-down:before { content: "\f0d7"; }
.fa-caret-right:before { content: "\f0da"; }
.fa-plus:before { content: "\f067"; }
.fa-play:before { content: "\f04b"; }
.fa-stop:before { content: "\f04d"; }
.fa-sync-alt:before { content: "\f2f1"; }
.fa-camera:before { content: "\f030"; }
.fa-info-circle:before { content: "\f05a"; }
.fa-external-link-alt:before { content: "\f35d"; }
.fa-circle:before { content: "\f111"; }
.fa-th-large:before { content: "\f009"; }
EOF

echo "Done! Update your base.html to use local-fontawesome.css instead of all.min.css."