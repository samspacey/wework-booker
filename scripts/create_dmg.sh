#!/bin/bash
# Create a DMG disk image for distribution
set -e

echo "=== Creating DMG for WeWork Booker ==="

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

APP_NAME="WeWork Booker"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="WeWorkBooker"
VERSION="0.1.0"
DMG_PATH="dist/${DMG_NAME}_${VERSION}.dmg"
DMG_TEMP="dist/${DMG_NAME}_temp.dmg"
VOLUME_NAME="${APP_NAME}"

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: App bundle not found at $APP_PATH"
    echo "Run ./scripts/build_mac.sh first"
    exit 1
fi

# Remove old DMG if exists
rm -f "$DMG_PATH" "$DMG_TEMP"

# Create a temporary directory for DMG contents
DMG_CONTENTS="dist/dmg_contents"
rm -rf "$DMG_CONTENTS"
mkdir -p "$DMG_CONTENTS"

# Copy app to DMG contents
echo "Copying app to DMG contents..."
cp -R "$APP_PATH" "$DMG_CONTENTS/"

# Create symlink to Applications folder
ln -s /Applications "$DMG_CONTENTS/Applications"

# Calculate size (add 50MB buffer for filesystem overhead)
SIZE=$(du -sm "$DMG_CONTENTS" | cut -f1)
SIZE=$((SIZE + 50))

echo "Creating DMG (${SIZE}MB)..."

# Create temporary DMG
hdiutil create -srcfolder "$DMG_CONTENTS" -volname "$VOLUME_NAME" -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" -format UDRW -size ${SIZE}m "$DMG_TEMP"

# Mount it
echo "Mounting DMG for customization..."
DEVICE=$(hdiutil attach -readwrite -noverify "$DMG_TEMP" | egrep '^/dev/' | sed 1q | awk '{print $1}')
MOUNT_POINT="/Volumes/${VOLUME_NAME}"

sleep 2

# Set background and icon positions using AppleScript
echo "Customizing DMG appearance..."
osascript << EOF
tell application "Finder"
    tell disk "${VOLUME_NAME}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set bounds of container window to {100, 100, 600, 400}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 80
        set position of item "${APP_NAME}.app" of container window to {125, 150}
        set position of item "Applications" of container window to {375, 150}
        close
        open
        update without registering applications
        delay 2
    end tell
end tell
EOF

# Unmount
sync
hdiutil detach "$DEVICE"

# Convert to compressed DMG
echo "Compressing DMG..."
hdiutil convert "$DMG_TEMP" -format UDZO -imagekey zlib-level=9 -o "$DMG_PATH"

# Cleanup
rm -f "$DMG_TEMP"
rm -rf "$DMG_CONTENTS"

echo ""
echo "=== DMG created successfully ==="
echo "DMG: $DMG_PATH"
echo ""
echo "File size: $(du -h "$DMG_PATH" | cut -f1)"
