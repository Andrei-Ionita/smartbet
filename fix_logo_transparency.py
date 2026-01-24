from PIL import Image

def make_transparent(input_path, output_path):
    print(f"Processing {input_path}...")
    img = Image.open(input_path)
    img = img.convert("RGBA")
    datas = img.getdata()

    new_data = []
    removed_count = 0
    
    # Threshold for "light" pixels (checkerboard white AND gray)
    # White = 255. Gray = 200/201.
    # We choose 190 to catch 200+
    # Logo colors (Navy/Green) are < 190 in at least one channel.
    THRESHOLD = 190 

    for item in datas:
        # Check if R, G, and B are all high (light color)
        if item[0] > THRESHOLD and item[1] > THRESHOLD and item[2] > THRESHOLD:
            new_data.append((255, 255, 255, 0)) # Transparent
            removed_count += 1
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved {output_path}")
    print(f"Removed {removed_count} pixels ({(removed_count/len(datas))*100:.1f}%)")

try:
    make_transparent(
        "c:/Users/Andrei/OneDrive/Desktop/ML/smartbet/smartbet-frontend/public/images/logo-final-v4.png",
        "c:/Users/Andrei/OneDrive/Desktop/ML/smartbet/smartbet-frontend/public/images/logo-final-v6.png"
    )
except Exception as e:
    print(f"Error: {e}")
