from PIL import Image, ImageDraw, ImageFont

# Create a new 32x32 image with white background (RGBA mode)
favicon_size = (32, 32)
image = Image.new('RGBA', favicon_size, (255, 255, 255, 0))

# Initialize drawing object
draw = ImageDraw.Draw(image)

# Option 1: Draw a solid color rectangle (replace with your design)
draw.rectangle([0, 0, 32, 32], fill=(0, 102, 204))  # A blue background

# Option 2: Add text to the favicon (optional)
# You can install a TTF font if desired, or use a basic system font
try:
    font = ImageFont.truetype("arial.ttf", 12)  # Path to a TTF font file
except IOError:
    font = ImageFont.load_default()

text = "CI"  # Example text for "CineIntellect"

# Use textbbox to calculate text size and position
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
text_position = ((favicon_size[0] - text_width) // 2, (favicon_size[1] - text_height) // 2)

# Draw text onto the image
draw.text(text_position, text, font=font, fill="white")

# Save the image as favicon.ico
image.save('favicon.png', format='PNG')

print("favicon.png created successfully!")
