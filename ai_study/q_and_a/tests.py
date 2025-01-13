import base64

# Provide the correct path to your image file
file_path =   f"C:/Users/hario/Downloads/ml_certificate_page-0001.jpg"  # Update this to the actual path of the image
output_file = "encoded_image.txt"    # The output file where the base64 string will be saved

# Open the image and encode to base64
with open(file_path, "rb") as f:
    encoded_string = base64.b64encode(f.read()).decode('utf-8')

# Write the encoded base64 string to the output text file
with open(output_file, "w") as output:
    output.write(encoded_string)

print(f"Base64 encoded image saved to {output_file}")
