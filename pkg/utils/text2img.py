from PIL import Image, ImageDraw, ImageFont
import re
import os

text_render_font = ImageFont.truetype("res/simhei.ttf", 32, encoding="utf-8")


def indexNumber(path=''):
    """
    查找字符串中数字所在串中的位置
    :param path:目标字符串
    :return:<class 'list'>: <class 'list'>: [['1', 16], ['2', 35], ['1', 51]]
    """
    kv = []
    nums = []
    beforeDatas = re.findall('[\d]+', path)
    for num in beforeDatas:
        indexV = []
        times = path.count(num)
        if times > 1:
            if num not in nums:
                indexs = re.finditer(num, path)
                for index in indexs:
                    iV = []
                    i = index.span()[0]
                    iV.append(num)
                    iV.append(i)
                    kv.append(iV)
            nums.append(num)
        else:
            index = path.find(num)
            indexV.append(num)
            indexV.append(index)
            kv.append(indexV)
    # 根据数字位置排序
    indexSort = []
    resultIndex = []
    for vi in kv:
        indexSort.append(vi[1])
    indexSort.sort()
    for i in indexSort:
        for v in kv:
            if i == v[1]:
                resultIndex.append(v)
    return resultIndex


def get_size(file):
    # 获取文件大小:KB
    size = os.path.getsize(file)
    return size / 1024


def get_outfile(infile, outfile):
    if outfile:
        return outfile
    dir, suffix = os.path.splitext(infile)
    outfile = '{}-out{}'.format(dir, suffix)
    return outfile


def compress_image(infile, outfile='', kb=100, step=20, quality=90):
    """不改变图片尺寸压缩到指定大小
    :param infile: 压缩源文件
    :param outfile: 压缩文件保存地址
    :param mb: 压缩目标,KB
    :param step: 每次调整的压缩比率
    :param quality: 初始压缩比率
    :return: 压缩文件地址，压缩文件大小
    """
    o_size = get_size(infile)
    if o_size <= kb:
        return infile
    outfile = get_outfile(infile, outfile)
    while o_size > kb:
        im = Image.open(infile)
        im.save(outfile, quality=quality)
        if quality - step < 0:
            break
        quality -= step
        o_size = get_size(outfile)
    return outfile, get_size(outfile)


def text_to_image(text_str, save_as="temp.png", width=800):
    global text_render_font
    # 文字分行
    
    # 分行
    lines = text_str.split('\n')

    # 计算并分割
    final_lines = []

    text_width = width-40
    for line in lines:
        # 如果长了就分割
        line_width = text_render_font.getlength(line)
        if line_width < text_width:
            final_lines.append(line)
            continue
        else:
            rest_text = line
            while True:
                # 分割最前面的一行
                point = int(len(rest_text) * (text_width / line_width))

                # 检查断点是否在数字中间
                numbers = indexNumber(rest_text)

                for number in numbers:
                    if number[1] < point < number[1] + len(number[0]) and number[1] != 0:
                        point = number[1]
                        break

                final_lines.append(rest_text[:point])
                rest_text = rest_text[point:]
                line_width = text_render_font.getlength(rest_text)
                if line_width < text_width:
                    final_lines.append(rest_text)
                    break
                else:
                    continue
    # 准备画布
    img = Image.new('RGBA', (width, max(280, len(final_lines) * 35 + 35)), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img, mode='RGBA')

    
    # 绘制正文
    line_number = 0
    offset_x = 20
    offset_y = 20
    for final_line in final_lines:
        draw.text((offset_x, offset_y + 35 * line_number), final_line, fill=(0, 0, 0), font=text_render_font)
        # 遍历此行,检查是否有emoji
        idx_in_line = 0
        for ch in final_line:
            # if self.is_emoji(ch):
            #     emoji_img_valid = ensure_emoji(hex(ord(ch))[2:])
            #     if emoji_img_valid:  # emoji图像可用,绘制到指定位置
            #         emoji_image = Image.open("emojis/{}.png".format(hex(ord(ch))[2:]), mode='r').convert('RGBA')
            #         emoji_image = emoji_image.resize((32, 32))

            #         x, y = emoji_image.size

            #         final_emoji_img = Image.new('RGBA', emoji_image.size, (255, 255, 255))
            #         final_emoji_img.paste(emoji_image, (0, 0, x, y), emoji_image)

            #         img.paste(final_emoji_img, box=(int(offset_x + idx_in_line * 32), offset_y + 35 * line_number))

            # 检查字符占位宽
            char_code = ord(ch)
            if char_code >= 127:
                idx_in_line += 1
            else:
                idx_in_line += 0.5

        line_number += 1

    
    img.save(save_as)

    return save_as
