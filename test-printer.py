#!/usr/bin/env python
from escpos.printer import Network
from PIL import Image
import time
import os
from dotenv import load_dotenv

def main():
    """Test script for thermal receipt printer."""
    # Load environment variables
    load_dotenv()
    printer_ip = os.getenv("PRINTER_IP")
    
    if not printer_ip:
        print("Error: PRINTER_IP not set in .env file")
        return
    
    try:
        # Connect to the printer
        print(f"Connecting to printer at {printer_ip}...")
        printer = Network(printer_ip)
        
        # Reset to default settings
        printer.set_with_default()

        # Print header
        printer.set(align='center')
        printer.text("RECEIPT PRINTER TEST\n")
        printer.text("Telegramtastic\n")
        printer.text("=" * 32 + "\n\n")
        
        printer.set_with_default()
        # Basic text styles
        printer.text("BASIC TEXT STYLES\n")
        printer.text("-" * 32 + "\n")
        
        # Normal text
        printer.text("Normal text\n")

        try:
            printer.set_with_default(font="b")
            printer.text("Normal text B\n")
        except Exception as e:
            print(f"Error setting font B: {e}")

        try:
            printer.set_with_default(font="c")
            printer.text("Normal text C\n")
        except Exception as e:
            print(f"Error setting font C: {e}")

        try:
            printer.set_with_default(font="d")
            printer.text("Normal text D\n")
        except Exception as e:
            print(f"Error setting font D: {e}")


        # Bold text
        printer.set(bold=True)
        printer.text("Bold text\n")
        # Reset bold
        printer.set(bold=False)
        
        # Double height
        printer.set(double_height=True)
        printer.text("Double height\n")
        printer.set_with_default() # set double_height=False does not work

        
        # Double width
        printer.set(double_width=True)
        printer.text("Double width\n")
        printer.set_with_default() # set double_width=False does not work

        # Underline
        printer.set(underline=1)
        printer.text("Underlined text\n")
        printer.set(underline=0)

        
        # Inverted colors
        try:
            printer.set(invert=True)
            printer.text("Inverted colors\n")
            printer.set(invert=False)
        except:
            printer.text("Inverted colors not supported\n\n")
        
        printer.text("\n")
        
        # Alignment demo
        # Reset to default settings
        printer.set_with_default()
        
        printer.text("ALIGNMENT DEMO\n")
        printer.text("-" * 32 + "\n")
        
        printer.set(align='left')
        printer.text("Left aligned\n")
        
        printer.set(align='center')
        printer.text("Center aligned\n")
        
        printer.set(align='right')
        printer.text("Right aligned\n")
        
        # Reset to left alignment
        printer.set(align='left')
        printer.text("\n")
        
        # Barcode demo
        # Reset to default settings
        printer.set_with_default()
        
        printer.text("BARCODE DEMO\n")
        printer.text("-" * 32 + "\n")
        
        # Code39 barcode
        printer.set(align='center')
        printer.barcode("123456789", "CODE39", height=100, width=2)
        printer.text("\nCODE39: 123456789\n\n")
        
        # EAN13 barcode
        printer.set(align='center')
        printer.barcode("5901234123457", "EAN13", height=100, width=2)
        printer.text("\nEAN13: 5901234123457\n\n")
        
        # ISBN13 barcode
        printer.set(align='center')
        printer.barcode("9781520126241", "ISBN13", height=100, width=2)
        printer.text("\nISBN13: 9781520126241\n\n")

        # Reset to default settings
        printer.set_with_default()
        
        # QR code demo
        printer.text("QR CODE DEMO\n")
        printer.text("-" * 32 + "\n")
        
        printer.set(align='center')
        printer.qr("https://github.com/python-escpos/python-escpos", size=8)
        printer.text("\nQR: python-escpos GitHub\n\n")
        
        # Reset to default settings
        printer.set_with_default()
        
        # Image demo
        printer.text("IMAGE DEMO\n")
        printer.text("-" * 32 + "\n")
        
        # Create a simple test image
        img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        
        # Draw some text
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("Arial", 30)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
        
        draw.text((10, 10), "Image Test", fill=(0, 0, 0), font=font)
        draw.rectangle([(20, 50), (380, 150)], outline=(0, 0, 0), width=5)
        draw.ellipse([(50, 70), (350, 130)], outline=(0, 0, 0), width=5)
        
        # Save the image temporarily
        img_path = "test_image.png"
        img.save(img_path)
        
        # Print the image
        printer.set(align='center')
        printer.image(img_path)
        printer.text("\nTest Image\n\n")
        
        # Clean up
        try:
            os.remove(img_path)
        except:
            pass
        
        # Reset to default settings one more time
        printer.set_with_default()
        
        # Footer
        printer.set(align='center')
        printer.text("=" * 32 + "\n")
        printer.text("Test completed at\n")
        printer.text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        printer.text("Thank you!\n\n\n\n")
        
        # Cut paper
        printer.cut()
        
        # Final reset of printer settings
        printer.set_with_default()
        
        print("Test completed successfully.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()