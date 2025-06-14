from PIL import Image, ImageDraw, ImageFont
import os

def generate_test_image():
    image_text = "Test OCR 123"
    image_filename = "test_image.png"
    # Ensure the tests directory exists
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(tests_dir, exist_ok=True)
    image_path = os.path.join(tests_dir, image_filename)

    # Image settings
    img_width = 200
    img_height = 100
    bg_color = "white"
    text_color = "black"

    # Create image
    img = Image.new('RGB', (img_width, img_height), color = bg_color)
    d = ImageDraw.Draw(img)

    # Attempt to load a font
    try:
        # Using a common default font path, adjust if necessary for your environment
        # For a truly portable solution, one might bundle a .ttf file or use a known system font
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except IOError:
        # Fallback to a basic default font if the specific one isn't found
        print("Default font not found, using load_default(). Text quality might be lower.")
        try:
            font = ImageFont.load_default()
        except IOError:
            print("Even default font failed. Text will not be rendered.")
            font = None # No text will be drawn

    if font:
        # Calculate text size and position
        # For Pillow 10.0.0 and later, use textbbox
        if hasattr(d, 'textbbox'):
            bbox = d.textbbox((0,0), image_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else: # For older Pillow versions, use textsize (deprecated)
            text_width, text_height = d.textsize(image_text, font=font)

        x = (img_width - text_width) / 2
        y = (img_height - text_height) / 2
        d.text((x, y), image_text, fill=text_color, font=font)
    else:
        # If no font, draw a rectangle as a placeholder
        d.rectangle([(10,10), (img_width-10, img_height-10)], fill="gray", outline="black")
        print(f"Warning: Font not found. Image {image_filename} created without text.")


    img.save(image_path)
    print(f"Test image '{image_filename}' created at '{image_path}'")

if __name__ == "__main__":
    generate_test_image()
