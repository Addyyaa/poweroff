from PIL import Image, ExifTags

# 读取图片分辨率信息
image = Image.open('C:/Users/SHEN/Desktop/微信图片_20240229104604.jpg')
image2 = Image.open('C:/Users/SHEN/Desktop/变横.jpg')
width, height = image.size
width2, height2 = image2.size
exif_data = image2.getexif()
if exif_data is not None:
    num = [2, 3, 4, 5, 6, 7, 8]
    for i in num:
        exif_data.update({0x0112: i})
        image2.save(f'C:/Users/SHEN/Desktop/new-{i}.jpg', exif=exif_data)
