"""
This module provides functions to download, convert, and compress images, and then convert them into a PDF file.

Copy right (c):-  Rahat4089 and VOATcb
Modified:- Dra-Sama
"""

from urllib.parse import quote
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from loguru import logger
import os

import pillow_avif  # This registers AVIF format support with Pillow
import pillow_heif

import requests
import shutil

from cloudscraper import create_scraper
import asyncio

import PyPDF2
import gc
from time import sleep



def get_headers(base_url: str):
    if "manhuaplus.com" in base_url:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://manhuaplus.com/",
            #"Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    elif "mangakatana.com" in base_url:
        headers = {
            "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            #"accept-encoding": "gzip, deflate, br, zstd"
            "accept-language": "en-GB,en;q=0.8",
            "connection": "keep-alive",
            #host: i.supernova22.click
            "referer": "https://mangakatana.com/",
            "sec-fetch-storage-access": "none",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        }
    elif "mangakakalot.gg" in base_url:
        headers = {
            "authority": "imgs-2.2xstorage.com",
            "method": "GET",
            "scheme": "https",
            "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://www.manganato.gg/",
            "sec-ch-ua": '"Chromium";v="137", "Not(A)Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "image",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"
        }
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": base_url,
        }

    return headers


async def thumbnali_images(image_url, download_dir, base_url = None, quality=80, file_name="thumb.jpg"):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    headers = get_headers(base_url) if base_url else {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    try:
        return await asyncio.to_thread(download_image, file_name, image_url, download_dir, cs=True, headers=headers)
    except:
        return None


def download_image(idx: str, image_url:str, download_dir: str, headers: dict = {}, cs: bool = False, quality: int = 80):
    idx = idx.zfill(5)
    img_path = os.path.join(download_dir, f"{idx}.jpg")
    for retries in range(3):
        try:
            session = requests.Session() if not cs else create_scraper()
            with session.get(image_url, stream=True, headers=headers, timeout=50) as image_response:
                if image_response.status_code == 200:
                    if os.path.exists(download_dir):
                        with open(img_path, 'wb') as img_file:
                            for chuck in image_response.iter_content(1024 * 64):
                                img_file.write(chuck)
                        
                        try:
                            with Image.open(img_path) as img:
                                img = img.convert("RGB")
                                img_width, img_height = img.size
                                img.save(img_path, "JPEG", quality=quality, optimize=True, progressive=True)
                        except Exception:
                            pass

                        return str(img_path)
                    else:
                        raise Exception("Tasks cancelled")
                
                elif "Attention Required! | Cloudflare" in str(image_response.text):
                    raise Exception("Cloudflare protection triggered")
                else:
                    logger.warning(f"Download :- {retries} :- {image_url}: {image_response.text}")
                    sleep(3 * (retries + 1))
            
                
        except Exception:
            sleep(3 * (retries + 1))
            logger.warning(f"Download :- {retries} :- {image_url}")
        
        finally:
            # Ensure session is close
            if 'session' in locals():
                try: session.close()
                except: pass
    
    if os.path.exists(img_path):
        os.remove(img_path)
    
    raise Exception("Failed to download image after 3 attempts")



async def download_and_convert_images(
    images, 
    download_dir,
    base_url: str,
    quality: int = 70, 
    cs: bool = False
):
    async def with_semaphore(*args, **kwargs):
        async with asyncio.Semaphore(5):
            return await asyncio.to_thread(download_image, *args, **kwargs)
    
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    image_files = [
        with_semaphore(
            str(idx), image_url, 
            download_dir, headers=get_headers(base_url), 
            cs=cs, quality=quality
        )
        for idx, image_url in enumerate(images, 1)
    ]

    picturesList = await asyncio.gather(*image_files)
    picturesList.sort()
    
    gc.collect()
    
    return picturesList


def get_min_width_generator(image_files):
    """Improved version with better memory management"""
    min_width = float('inf')

    for image_file in image_files:
        try:
            with Image.open(image_file) as img:
                width = img.width
                if width < min_width:
                    min_width = width
                if hasattr(img, 'close'):
                    img.close()
                del img
        except Exception:
            continue
    
    gc.collect()

    return min_width if min_width != float('inf') else None



def compress_image(image_path, output_path, quality=80, target_width=None):
    """Compress the image by resizing and reducing its quality."""
    try:
        img = Image.open(image_path).convert("RGB")
        img_width, img_height = img.size

        if target_width:
            new_height = int((target_width / img_width) * img_height)
            img = img.resize((target_width, new_height), Image.LANCZOS)

        img.save(output_path, "JPEG", quality=quality, progressive=True)

        return output_path, img_width, img_height
    except Exception as e:
        logger.warning(f"Error compressing image {image_path}: {e}")
        return image_path, 0, 0


def convert_images_to_pdf(image_files, pdf_output_path, compressed_dir, password=None, compression_quality=50):
    if not image_files:
        logger.warning("No images provided for PDF conversion.")
        return "No images provided for PDF conversion."
    
    os.makedirs(compressed_dir, exist_ok=True)
    temp_pdf_path = str(pdf_output_path).replace(".pdf", "_temp.pdf")

    c = canvas.Canvas(str(temp_pdf_path), pagesize=letter)

    # Set the target width (e.g., the width of the smallest image)
    target_width = get_min_width_generator(image_files)

    def draw_image(image_file, img_width, img_height):
        try:
            if target_width:
                new_height = int(target_width * img_height / img_width)
                c.setPageSize((target_width, new_height))
                c.drawImage(str(image_file), 0, 0, width=target_width, height=new_height)

            c.showPage()  # Create a new page for each image
        except Exception as e:
            logger.error(f"Failed to process image {image_file}: {e}")

    # Process and compress the images
    compressed_images = []
    for image_file in image_files:
        compressed_image_path = f"{compressed_dir}/{os.path.basename(image_file)}"
        compressed_image, img_width, img_height = compress_image(
            image_file, compressed_image_path, 
            quality=compression_quality, target_width=target_width
        )
        compressed_images.append(compressed_image)
        draw_image(compressed_image, img_width, img_height)

    c.save()

    if password:
        encrypt_pdf(temp_pdf_path, str(pdf_output_path), password)
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)  # Remove the temporary unprotected PDF
    else:
        os.rename(temp_pdf_path, str(pdf_output_path))

    shutil.rmtree(compressed_dir, ignore_errors=True)

    logger.info(f"Compressed PDF created at {pdf_output_path}")

    gc.collect()

    return None


def encrypt_pdf(input_path, output_path, password):
    """Encrypt a PDF with a password using PyPDF2"""
    try:
        with open(input_path, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            writer = PyPDF2.PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            writer.encrypt(user_password=password, owner_password=None, 
                          use_128bit=True)

            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

    except Exception as e:
        logger.error(f"Failed to encrypt PDF: {e}")
