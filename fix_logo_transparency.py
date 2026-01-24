from PIL import Image
import sys

def make_transparent(input_path, output_path):
    print(f"Processing {input_path}...")
    img = Image.open(input_path)
    img = img.convert("RGBA")
    datas = img.getdata()

    new_data = []
    # Threshold for "white" or "light gray" pixels to remove
    # Checking for the checkerboard gray/white pattern
    # The checkerboard is usually white (255,255,255) and light gray (around 204-240)
    for item in datas:
        # Check if pixel is close to white or the light gray of checkerboard
        # R, G, B > 200 is a safe bet for the background of this specific logo 
        # since the logo itself is dark navy and emerald green (very distinct)
        if item[0] > 200 and item[1] > 200 and item[2] > 200:
            new_data.append((255, 255, 255, 0)) # Make Transparent
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved transparent image to {output_path}")

try:
    make_transparent(
        "c:/Users/Andrei/OneDrive/Desktop/ML/smartbet/smartbet-frontend/public/images/logo-final-v4.png",
        "c:/Users/Andrei/OneDrive/Desktop/ML/smartbet/smartbet-frontend/public/images/logo-final-v5.png"
    )
except Exception as e:
    print(f"Error: {e}")
