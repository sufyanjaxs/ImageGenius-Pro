import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont, ImageChops, ImageOps, ImageMath
import colorsys
import math
import struct
import io
import os


class ImageEditor:

    @staticmethod
    def apply_filter(image, filter_type, params=None):
        if params is None:
            params = {}

        if filter_type == 'blur':
            radius = int(params.get('radius', 5))
            return image.filter(ImageFilter.GaussianBlur(radius=radius))

        elif filter_type == 'box_blur':
            radius = int(params.get('radius', 3))
            return image.filter(ImageFilter.BoxBlur(radius))

        elif filter_type == 'motion_blur':
            img = np.array(image)
            direction = int(params.get('direction', 0))
            intensity = int(params.get('intensity', 10))
            kernel_size = max(1, intensity)

            kernel = np.zeros((kernel_size, kernel_size))
            rad = math.radians(direction)
            cx = kernel_size // 2
            cy = kernel_size // 2

            for i in range(kernel_size):
                t = (i / kernel_size) * 2 - 1
                dx = int(round(t * cx * math.cos(rad)))
                dy = int(round(t * cy * math.sin(rad)))
                kx = cx + dx
                ky = cy + dy
                if 0 <= kx < kernel_size and 0 <= ky < kernel_size:
                    kernel[ky, kx] = 1

            kernel_sum = kernel.sum()
            if kernel_sum > 0:
                kernel = kernel / kernel_sum

            from scipy import signal
            result = np.zeros_like(img, dtype=np.float64)
            for c in range(3):
                result[:,:,c] = signal.convolve2d(img[:,:,c], kernel, mode='same', boundary='symm')

            return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))

        elif filter_type == 'sharpen':
            factor = float(params.get('factor', 2.0))
            sharp = ImageFilter.UnsharpMask(radius=2, percent=int(factor * 100), threshold=0)
            return image.filter(sharp)

        elif filter_type == 'edge_detect':
            edge_filter = ImageFilter.FIND_EDGES
            edges = image.filter(edge_filter)
            amount = float(params.get('amount', 1.0))
            if amount != 1.0:
                edges = ImageEnhance.Brightness(edges).enhance(amount)
            return edges

        elif filter_type == 'emboss':
            return image.filter(ImageFilter.EMBOSS)

        elif filter_type == 'contour':
            return image.filter(ImageFilter.CONTOUR)

        elif filter_type == 'smooth':
            return image.filter(ImageFilter.SMOOTH)

        elif filter_type == 'detail':
            return image.filter(ImageFilter.DETAIL)

        elif filter_type == 'sepia':
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img = np.array(image, dtype=np.float64)
            r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]
            tr = r * 0.393 + g * 0.769 + b * 0.189
            tg = r * 0.349 + g * 0.686 + b * 0.168
            tb = r * 0.272 + g * 0.534 + b * 0.131
            img[:,:,0] = np.clip(tr, 0, 255)
            img[:,:,1] = np.clip(tg, 0, 255)
            img[:,:,2] = np.clip(tb, 0, 255)
            amount = float(params.get('amount', 1.0))
            if amount != 1.0:
                orig = np.array(image, dtype=np.float64)
                img = orig * (1 - amount) + img * amount
            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif filter_type == 'pencil_sketch':
            gray = image.convert('L')
            inv = ImageOps.invert(gray)
            blurred = inv.filter(ImageFilter.GaussianBlur(radius=int(params.get('radius', 5))))
            sketch = ImageChops.dodge(gray, blurred)
            return sketch.convert('RGB')

        elif filter_type == 'oil_painting':
            img = np.array(image)
            radius = int(params.get('radius', 4))
            intensity = int(params.get('intensity', 10))
            result = np.zeros_like(img)

            h, w = img.shape[:2]
            for y in range(h):
                for x in range(w):
                    y_min = max(0, y - radius)
                    y_max = min(h, y + radius + 1)
                    x_min = max(0, x - radius)
                    x_max = min(w, x + radius + 1)

                    region = img[y_min:y_max, x_min:x_max]

                    gray = np.mean(region, axis=2).astype(np.int32)
                    levels = gray // (256 // intensity)

                    best_count = 0
                    best_color = np.array([0, 0, 0])

                    for l in range(intensity):
                        mask = levels == l
                        count = np.sum(mask)
                        if count > best_count:
                            best_count = count
                            if count > 0:
                                best_color = np.mean(region[mask], axis=0)

                    result[y, x] = best_color

            return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))

        elif filter_type == 'pixelate':
            pixel_size = max(1, int(params.get('pixel_size', 10)))
            small = image.resize(
                (max(1, image.width // pixel_size), max(1, image.height // pixel_size)),
                Image.NEAREST
            )
            return small.resize((image.width, image.height), Image.NEAREST)

        elif filter_type == 'mosaic':
            img = np.array(image)
            tile_size = max(2, int(params.get('tile_size', 20)))
            h, w = img.shape[:2]

            for y in range(0, h, tile_size):
                for x in range(0, w, tile_size):
                    y2 = min(y + tile_size, h)
                    x2 = min(x + tile_size, w)
                    tile = img[y:y2, x:x2]
                    avg = tile.mean(axis=(0, 1)).astype(np.uint8)
                    img[y:y2, x:x2] = avg

            return Image.fromarray(img)

        elif filter_type == 'posterize':
            bits = int(params.get('bits', 4))
            return ImageOps.posterize(image, bits)

        elif filter_type == 'solarize':
            threshold = int(params.get('threshold', 128))
            return ImageOps.solarize(image, threshold)

        elif filter_type == 'equalize':
            return ImageOps.equalize(image)

        elif filter_type == 'invert':
            if image.mode == 'RGBA':
                r, g, b, a = image.split()
                rgb = Image.merge('RGB', (r, g, b))
                inv = ImageOps.invert(rgb)
                ir, ig, ib = inv.split()
                return Image.merge('RGBA', (ir, ig, ib, a))
            return ImageOps.invert(image)

        elif filter_type == 'grayscale':
            return image.convert('L').convert('RGB')

        elif filter_type == 'vignette':
            img = np.array(image.convert('RGB'), dtype=np.float64)
            h, w = img.shape[:2]
            cx, cy = w / 2, h / 2
            max_dist = math.sqrt(cx**2 + cy**2)

            for y in range(h):
                for x in range(w):
                    dx = (x - cx) / cx
                    dy = (y - cy) / cy
                    dist = math.sqrt(dx*dx + dy*dy)
                    vignette = 1.0 - dist * dist * 0.5
                    vignette = max(0.2, vignette)
                    img[y, x] = img[y, x] * vignette

            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif filter_type == 'noise':
            img = np.array(image, dtype=np.float64)
            amount = float(params.get('amount', 20))
            noise = np.random.normal(0, amount, img.shape)
            return Image.fromarray(np.clip(img + noise, 0, 255).astype(np.uint8))

        elif filter_type == 'glow':
            img = image.filter(ImageFilter.GaussianBlur(radius=int(params.get('radius', 10))))
            alpha = float(params.get('alpha', 0.5))
            return Image.blend(image, img, alpha)

        elif filter_type == 'neon':
            img = image.filter(ImageFilter.FIND_EDGES)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(2.0)
            if image.mode == 'RGB':
                img = img.convert('RGB')
            return img

        elif filter_type == 'cartoon':
            img = np.array(image)
            gray = np.mean(img, axis=2)
            edges = np.zeros_like(gray)
            gy, gx = np.gradient(gray)
            edges = np.sqrt(gx**2 + gy**2)
            edge_mask = edges > int(params.get('threshold', 30))

            quantized = (img // 64) * 64 + 32
            quantized[edge_mask] = [0, 0, 0]

            return Image.fromarray(np.clip(quantized, 0, 255).astype(np.uint8))

        elif filter_type == 'dream':
            for _ in range(int(params.get('iterations', 3))):
                image = image.filter(ImageFilter.GaussianBlur(radius=2))
                image = ImageEnhance.Color(image).enhance(1.2)
            return image

        elif filter_type == 'thermal':
            img = np.array(image.convert('RGB'), dtype=np.float64)
            gray = np.mean(img, axis=2)
            result = np.zeros_like(img)
            for y in range(img.shape[0]):
                for x in range(img.shape[1]):
                    v = gray[y, x] / 255.0
                    if v < 0.25:
                        r, g, b = 0, 0, 127 + v * 4 * 128
                    elif v < 0.5:
                        r = (v - 0.25) * 4 * 255
                        g = (v - 0.25) * 4 * 200
                        b = 255 - (v - 0.25) * 4 * 128
                    elif v < 0.75:
                        r = 255
                        g = (v - 0.5) * 4 * 255
                        b = (v - 0.5) * 4 * 100
                    else:
                        r = 255
                        g = 255 - (v - 0.75) * 4 * 128
                        b = 0
                    result[y, x] = [max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b)))]
            return Image.fromarray(result.astype(np.uint8))

        elif filter_type == 'emboss_deep':
            kernel = ImageFilter.Kernel((3, 3), [
                -2, -1, 0,
                -1,  1, 1,
                 0,  1, 2
            ], scale=1, offset=128)
            return image.filter(kernel)

        elif filter_type == 'custom_kernel':
            kernel_data = params.get('kernel', '0,0,0;0,1,0;0,0,0')
            size = params.get('kernel_size', 3)
            rows = kernel_data.split(';')
            values = []
            for row in rows:
                values.extend([float(v) for v in row.split(',')])
            k = ImageFilter.Kernel((size, size), values, scale=sum(values) if sum(values) != 0 else 1)
            return image.filter(k)

        return image

    @staticmethod
    def adjust(image, adjustment_type, value):
        if image.mode != 'RGB' and image.mode != 'RGBA':
            image = image.convert('RGB')

        if adjustment_type == 'brightness':
            factor = float(value)
            return ImageEnhance.Brightness(image).enhance(factor)

        elif adjustment_type == 'contrast':
            factor = float(value)
            return ImageEnhance.Contrast(image).enhance(factor)

        elif adjustment_type == 'saturation':
            factor = float(value)
            return ImageEnhance.Color(image).enhance(factor)

        elif adjustment_type == 'sharpness':
            factor = float(value)
            return ImageEnhance.Sharpness(image).enhance(factor)

        elif adjustment_type == 'hue':
            shift = float(value)
            img = np.array(image.convert('RGB'), dtype=np.float64)
            r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]
            for y in range(img.shape[0]):
                for x in range(img.shape[1]):
                    h, s, v = colorsys.rgb_to_hsv(r[y,x]/255, g[y,x]/255, b[y,x]/255)
                    h = (h + shift) % 1.0
                    nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
                    r[y,x], g[y,x], b[y,x] = nr*255, ng*255, nb*255
            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif adjustment_type == 'gamma':
            gamma_val = float(value)
            if gamma_val <= 0:
                gamma_val = 0.1
            img = np.array(image.convert('RGB'), dtype=np.float64) / 255.0
            img = np.power(img, gamma_val) * 255
            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif adjustment_type == 'exposure':
            ev = float(value)
            factor = 2.0 ** ev
            return ImageEnhance.Brightness(image).enhance(factor)

        elif adjustment_type == 'vibrance':
            amount = float(value)
            img = np.array(image.convert('RGB'), dtype=np.float64)
            for y in range(img.shape[0]):
                for x in range(img.shape[1]):
                    r, g, b = img[y,x]
                    gray = (r + g + b) / 3
                    max_val = max(r, g, b)
                    if max_val > 0:
                        saturation = (max_val - min(r, g, b)) / max_val
                        boost = 1.0 + amount * (1.0 - saturation)
                        r = gray + (r - gray) * boost
                        g = gray + (g - gray) * boost
                        b = gray + (b - gray) * boost
                        img[y,x] = [r, g, b]
            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif adjustment_type == 'temperature':
            temp = float(value)
            img = np.array(image.convert('RGB'), dtype=np.float64)
            if temp > 0:
                img[:,:,0] *= (1 + temp * 0.1)
                img[:,:,2] *= (1 - temp * 0.05)
            else:
                img[:,:,0] *= (1 + temp * 0.05)
                img[:,:,2] *= (1 - temp * 0.1)
            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif adjustment_type == 'tint':
            tint = float(value)
            img = np.array(image.convert('RGB'), dtype=np.float64)
            if tint > 0:
                img[:,:,1] *= (1 + tint * 0.05)
                img[:,:,2] *= (1 + tint * 0.1)
            else:
                img[:,:,0] *= (1 - tint * 0.05)
                img[:,:,1] *= (1 - tint * 0.05)
            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif adjustment_type == 'highlights':
            amount = float(value)
            img = np.array(image.convert('RGB'), dtype=np.float64)
            gray = np.mean(img, axis=2)
            mask = gray > 128
            for c in range(3):
                img[:,:,c][mask] += amount * (255 - img[:,:,c][mask]) * 0.5
            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif adjustment_type == 'shadows':
            amount = float(value)
            img = np.array(image.convert('RGB'), dtype=np.float64)
            gray = np.mean(img, axis=2)
            mask = gray < 128
            for c in range(3):
                img[:,:,c][mask] += amount * img[:,:,c][mask] * 0.5
            return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

        elif adjustment_type == 'auto_contrast':
            return ImageOps.autocontrast(image, cutoff=int(params.get('cutoff', 0)))

        elif adjustment_type == 'auto_color':
            return ImageOps.colorize(image.convert('L'), (0, 0, 0), (255, 255, 255))

        return image

    @staticmethod
    def transform(image, transform_type, params=None):
        if params is None:
            params = {}

        if transform_type == 'resize':
            w = int(params.get('width', image.width))
            h = int(params.get('height', image.height))
            keep_aspect = params.get('keep_aspect', 'true').lower() == 'true'
            if keep_aspect:
                image.thumbnail((w, h), Image.LANCZOS)
                return image
            return image.resize((w, h), Image.LANCZOS)

        elif transform_type == 'crop':
            x = int(params.get('x', 0))
            y = int(params.get('y', 0))
            w = int(params.get('width', image.width))
            h = int(params.get('height', image.height))
            return image.crop((x, y, x + w, y + h))

        elif transform_type == 'rotate':
            angle = float(params.get('angle', 0))
            expand = params.get('expand', 'true').lower() == 'true'
            fill_color = params.get('fill_color', (0, 0, 0))
            if isinstance(fill_color, str):
                fill_color = tuple(int(fill_color[i:i+2], 16) for i in (1, 3, 5))
            return image.rotate(angle, expand=expand, fillcolor=fill_color, resample=Image.BICUBIC)

        elif transform_type == 'flip_horizontal':
            return ImageOps.mirror(image)

        elif transform_type == 'flip_vertical':
            return ImageOps.flip(image)

        elif transform_type == 'skew':
            img = np.array(image)
            h, w = img.shape[:2]
            skew_x = float(params.get('skew_x', 0))
            skew_y = float(params.get('skew_y', 0))

            from scipy import ndimage
            transform_matrix = np.array([[1, skew_x, 0], [skew_y, 1, 0], [0, 0, 1]])
            result = np.zeros_like(img)
            for c in range(3):
                result[:,:,c] = ndimage.affine_transform(img[:,:,c], transform_matrix, order=3)
            return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))

        elif transform_type == 'perspective':
            img = np.array(image)
            h, w = img.shape[:2]
            tl = params.get('tl', (0, 0))
            tr = params.get('tr', (w, 0))
            bl = params.get('bl', (0, h))
            br = params.get('br', (w, h))
            src_pts = [(0, 0), (w, 0), (0, h), (w, h)]
            dst_pts = [tl, tr, bl, br]

            matrix = []
            for sp, dp in zip(src_pts, dst_pts):
                matrix.extend([
                    [sp[0], sp[1], 1, 0, 0, 0, -dp[0]*sp[0], -dp[0]*sp[1]],
                    [0, 0, 0, sp[0], sp[1], 1, -dp[1]*sp[0], -dp[1]*sp[1]]
                ])
            A = np.array(matrix)
            B = np.array([p for pt in dst_pts for p in pt])
            try:
                H = np.linalg.lstsq(A, B, rcond=None)[0]
                H = np.append(H, 1).reshape(3, 3)
                from scipy import ndimage
                result = np.zeros_like(img)
                for c in range(3):
                    result[:,:,c] = ndimage.affine_transform(img[:,:,c], np.linalg.inv(H), order=3, offset=0)
                return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))
            except:
                return image

        elif transform_type == 'scale':
            scale_factor = float(params.get('scale', 1.0))
            new_w = max(1, int(image.width * scale_factor))
            new_h = max(1, int(image.height * scale_factor))
            return image.resize((new_w, new_h), Image.LANCZOS)

        elif transform_type == 'trim':
            fuzz = int(params.get('fuzz', 0))
            bg = Image.new(image.mode, image.size, image.getpixel((0,0)))
            diff = ImageChops.difference(image, bg)
            bbox = diff.getbbox()
            if bbox:
                return image.crop(bbox)
            return image

        return image

    @staticmethod
    def draw_text(image, params):
        img = image.copy()
        draw = ImageDraw.Draw(img)
        text = params.get('text', 'Text')
        x = int(params.get('x', 50))
        y = int(params.get('y', 50))
        size = int(params.get('size', 32))
        color = params.get('color', '#ffffff')
        if isinstance(color, str):
            color = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        opacity = int(params.get('opacity', 255))
        rotation = float(params.get('rotation', 0))
        font_path = params.get('font', None)
        bold = params.get('bold', 'false').lower() == 'true'
        italic = params.get('italic', 'false').lower() == 'true'
        underline = params.get('underline', 'false').lower() == 'true'
        stroke_width = int(params.get('stroke_width', 0))
        stroke_color = params.get('stroke_color', '#000000')
        if isinstance(stroke_color, str):
            stroke_color = tuple(int(stroke_color[i:i+2], 16) for i in (1, 3, 5))

        try:
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        if rotation != 0:
            txt_img = Image.new('RGBA', (img.width, img.height), (0, 0, 0, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text((x, y), text, font=font, fill=(*color, opacity),
                          stroke_width=stroke_width, stroke_color=stroke_color)
            txt_img = txt_img.rotate(rotation, expand=False, center=(x, y))
            img = Image.alpha_composite(img.convert('RGBA'), txt_img)
        else:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            draw = ImageDraw.Draw(img)
            draw.text((x, y), text, font=font, fill=(*color, opacity),
                      stroke_width=stroke_width, stroke_color=stroke_color)

        return img

    @staticmethod
    def draw_shape(image, params):
        img = image.copy()
        draw = ImageDraw.Draw(img)

        shape_type = params.get('shape', 'rectangle')
        x1 = int(params.get('x1', 50))
        y1 = int(params.get('y1', 50))
        x2 = int(params.get('x2', 200))
        y2 = int(params.get('y2', 200))
        color = params.get('color', '#ff0000')
        if isinstance(color, str):
            color = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        fill = params.get('fill', '')
        if isinstance(fill, str) and fill:
            fill = tuple(int(fill[i:i+2], 16) for i in (1, 3, 5))
        elif not fill:
            fill = None
        width = int(params.get('width', 2))
        opacity = int(params.get('opacity', 255))
        num_sides = max(3, int(params.get('sides', 6)))
        rotation = float(params.get('rotation', 0))

        if shape_type == 'rectangle':
            draw.rectangle([x1, y1, x2, y2], outline=color, fill=fill, width=width)

        elif shape_type == 'ellipse':
            draw.ellipse([x1, y1, x2, y2], outline=color, fill=fill, width=width)

        elif shape_type == 'circle':
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            r = max(1, min(abs(x2 - x1), abs(y2 - y1)) // 2)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, fill=fill, width=width)

        elif shape_type == 'line':
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

        elif shape_type == 'arrow':
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            angle = math.atan2(y2 - y1, x2 - x1)
            arrow_size = 15 + width
            for a in [angle + math.pi * 0.85, angle - math.pi * 0.85]:
                ex = x2 + arrow_size * math.cos(a)
                ey = y2 + arrow_size * math.sin(a)
                draw.line([(x2, y2), (ex, ey)], fill=color, width=width)

        elif shape_type == 'polygon':
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            rx = abs(x2 - x1) // 2
            ry = abs(y2 - y1) // 2
            pts = []
            for i in range(num_sides):
                a = math.radians(360 * i / num_sides - 90 + rotation)
                pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
            draw.polygon(pts, outline=color, fill=fill, width=width)

        elif shape_type == 'star':
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            outer_r = max(1, min(abs(x2 - x1), abs(y2 - y1)) // 2)
            inner_r = outer_r * 0.4
            pts = []
            for i in range(10):
                a = math.radians(36 * i - 90 + rotation)
                r = outer_r if i % 2 == 0 else inner_r
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            draw.polygon(pts, outline=color, fill=fill, width=width)

        return img

    @staticmethod
    def blend_layers(base, overlay, blend_mode='normal', opacity=1.0):
        if base.mode != 'RGBA':
            base = base.convert('RGBA')
        if overlay.mode != 'RGBA':
            overlay = overlay.convert('RGBA')

        base_arr = np.array(base, dtype=np.float64) / 255.0
        overlay_arr = np.array(overlay, dtype=np.float64) / 255.0

        a = base_arr[:,:,:3]
        b = overlay_arr[:,:,:3]

        if blend_mode == 'normal':
            result = b
        elif blend_mode == 'multiply':
            result = a * b
        elif blend_mode == 'screen':
            result = 1 - (1 - a) * (1 - b)
        elif blend_mode == 'overlay':
            mask = a < 0.5
            result = np.where(mask, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))
        elif blend_mode == 'darken':
            result = np.minimum(a, b)
        elif blend_mode == 'lighten':
            result = np.maximum(a, b)
        elif blend_mode == 'difference':
            result = np.abs(a - b)
        elif blend_mode == 'exclusion':
            result = a + b - 2 * a * b
        elif blend_mode == 'add':
            result = np.clip(a + b, 0, 1)
        elif blend_mode == 'subtract':
            result = np.clip(a - b, 0, 1)
        elif blend_mode == 'divide':
            result = np.clip(a / (b + 0.001), 0, 1)
        elif blend_mode == 'dodge':
            result = np.clip(a / (1 - b + 0.001), 0, 1)
        elif blend_mode == 'burn':
            result = 1 - np.clip((1 - a) / (b + 0.001), 0, 1)
        elif blend_mode == 'soft_light':
            result = np.where(b <= 0.5,
                              a - (1 - 2 * b) * a * (1 - a),
                              a + (2 * b - 1) * (np.sqrt(a) - a))
        elif blend_mode == 'hard_light':
            mask = b < 0.5
            result = np.where(mask, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))
        elif blend_mode == 'color_dodge':
            result = np.clip(a / (1 - b + 0.001), 0, 1)
        elif blend_mode == 'color_burn':
            result = 1 - np.clip((1 - a) / (b + 0.001), 0, 1)
        elif blend_mode == 'reflect':
            result = np.clip(b * b / (1 - a + 0.001), 0, 1)
        elif blend_mode == 'glow':
            result = np.clip(a * a / (1 - b + 0.001), 0, 1)
        elif blend_mode == 'freeze':
            result = 1 - np.clip((1 - b) * (1 - b) / (a + 0.001), 0, 1)
        elif blend_mode == 'heat':
            result = np.where(b == 0, a,
                              np.clip(a / b + b / (a + 0.001), 0, 1))
        elif blend_mode == 'negation':
            result = 1 - np.abs(1 - a - b)
        elif blend_mode == 'phoenix':
            result = np.clip(np.minimum(a, b) - np.maximum(a, b) + 1, 0, 1)
        elif blend_mode == 'pin_light':
            result = np.where(b <= 0.5, np.minimum(a, 2 * b), np.maximum(a, 2 * b - 1))
        elif blend_mode == 'vivid_light':
            result = np.where(b <= 0.5,
                              1 - (1 - a) / (2 * b + 0.001),
                              a / (2 * (1 - b) + 0.001))
            result = np.clip(result, 0, 1)
        elif blend_mode == 'linear_dodge':
            result = np.clip(a + b, 0, 1)
        elif blend_mode == 'linear_burn':
            result = np.clip(a + b - 1, 0, 1)
        else:
            result = b

        if opacity < 1.0:
            result = a * (1 - opacity) + result * opacity

        result = np.clip(result, 0, 1)

        out_alpha = np.clip(base_arr[:,:,3] + overlay_arr[:,:,3] * opacity, 0, 1)
        out = np.dstack((result, out_alpha))

        return Image.fromarray((out * 255).astype(np.uint8))

    @staticmethod
    def apply_gradient_map(image, colors):
        img = np.array(image.convert('RGB'))
        gray = np.mean(img, axis=2)

        if len(colors) < 2:
            return image

        result = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
        for y in range(img.shape[0]):
            for x in range(img.shape[1]):
                t = gray[y, x] / 255.0
                segments = len(colors) - 1
                seg = t * segments
                idx = min(int(seg), segments - 1)
                local_t = seg - idx
                c1 = colors[idx]
                c2 = colors[min(idx + 1, segments - 1)]
                r = int(c1[0] + (c2[0] - c1[0]) * local_t)
                g = int(c1[1] + (c2[1] - c1[1]) * local_t)
                b = int(c1[2] + (c2[2] - c1[2]) * local_t)
                result[y, x] = [max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))]

        return Image.fromarray(result, 'RGB')

    @staticmethod
    def channel_mixer(image, red=(1, 0, 0), green=(0, 1, 0), blue=(0, 0, 1)):
        img = np.array(image.convert('RGB'), dtype=np.float64)
        r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]
        result = np.zeros_like(img)
        result[:,:,0] = r * red[0] + g * red[1] + b * red[2]
        result[:,:,1] = r * green[0] + g * green[1] + b * green[2]
        result[:,:,2] = r * blue[0] + g * blue[1] + b * blue[2]
        return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))

    @staticmethod
    def color_balance(image, shadows=(0, 0, 0), midtones=(0, 0, 0), highlights=(0, 0, 0)):
        img = np.array(image.convert('RGB'), dtype=np.float64)
        result = np.zeros_like(img)
        h, w = img.shape[:2]
        for y in range(h):
            for x in range(w):
                gray = np.mean(img[y, x])
                if gray < 85:
                    factor = (85 - gray) / 85
                    result[y, x] = img[y, x] + np.array(shadows) * factor
                elif gray < 170:
                    factor = (gray - 85) / 85
                    result[y, x] = img[y, x] + np.array(midtones) * factor
                else:
                    factor = (gray - 170) / 85
                    result[y, x] = img[y, x] + np.array(highlights) * factor
        return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))

    @staticmethod
    def lens_flare(image, x=None, y=None, brightness=0.5):
        img = np.array(image.convert('RGB'), dtype=np.float64)
        h, w = img.shape[:2]

        if x is None:
            x = w * 0.3
        if y is None:
            y = h * 0.3

        flare = np.zeros((h, w, 3), dtype=np.float64)
        for i in range(10):
            radius = (i + 1) * 20
            alpha = brightness * (0.5 - i * 0.05)
            if alpha <= 0:
                break

            def draw_ring(cx, cy, r, a):
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if dx*dx + dy*dy <= r*r:
                            px = int(cx + dx)
                            py = int(cy + dy)
                            if 0 <= px < w and 0 <= py < h:
                                flare[py, px] += a * (1 - (dx*dx + dy*dy) / (r*r))

            draw_ring(x, y, radius, alpha * 0.3)
            draw_ring(x + radius * 0.3, y + radius * 0.5, radius // 3, alpha)

        flare = np.clip(flare, 0, 1)
        img = img / 255.0 * (1 - flare * 0.5) + flare * 0.5
        return Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8))

    @staticmethod
    def kaleidoscope(image, segments=8):
        img = np.array(image.convert('RGB'))
        h, w = img.shape[:2]
        cx, cy = w / 2, h / 2
        result = np.zeros_like(img)
        angle_step = 2 * math.pi / segments

        for y in range(h):
            for x in range(w):
                dx = x - cx
                dy = y - cy
                r = math.sqrt(dx*dx + dy*dy)
                angle = math.atan2(dy, dx)
                if angle < 0:
                    angle += 2 * math.pi

                seg = int(angle / angle_step)
                mirror = seg % 2 == 1
                mapped_angle = seg * angle_step
                if mirror:
                    mapped_angle += angle_step - (angle - mapped_angle)
                else:
                    mapped_angle += (angle - mapped_angle)

                sx = int(cx + r * math.cos(mapped_angle))
                sy = int(cy + r * math.sin(mapped_angle))
                if 0 <= sx < w and 0 <= sy < h:
                    result[y, x] = img[sy, sx]

        return Image.fromarray(result)

    @staticmethod
    def wave_distort(image, amplitude=10, frequency=0.05, direction='horizontal'):
        img = np.array(image)
        h, w = img.shape[:2]
        result = np.zeros_like(img)

        for y in range(h):
            for x in range(w):
                if direction == 'horizontal':
                    offset = int(amplitude * math.sin(y * frequency * 2 * math.pi))
                    sx = x + offset
                    sy = y
                else:
                    offset = int(amplitude * math.sin(x * frequency * 2 * math.pi))
                    sx = x
                    sy = y + offset

                if 0 <= sx < w and 0 <= sy < h:
                    result[y, x] = img[sy, sx]

        return Image.fromarray(result)

    @staticmethod
    def buldge(image, strength=1.0, cx=None, cy=None, radius=None):
        img = np.array(image)
        h, w = img.shape[:2]

        if cx is None:
            cx = w / 2
        if cy is None:
            cy = h / 2
        if radius is None:
            radius = min(w, h) * 0.4

        result = np.zeros_like(img)

        for y in range(h):
            for x in range(w):
                dx = x - cx
                dy = y - cy
                d = math.sqrt(dx*dx + dy*dy)

                if d < radius:
                    factor = 1 - (d / radius) ** 2
                    scale = 1 - strength * factor * 0.3
                    sx = int(cx + dx * scale)
                    sy = int(cy + dy * scale)
                    if 0 <= sx < w and 0 <= sy < h:
                        result[y, x] = img[sy, sx]
                    else:
                        result[y, x] = [0, 0, 0]
                else:
                    result[y, x] = img[y, x]

        return Image.fromarray(result)

    @staticmethod
    def ripple(image, amplitude=10, frequency=0.05):
        img = np.array(image)
        h, w = img.shape[:2]
        result = np.zeros_like(img)

        for y in range(h):
            for x in range(w):
                dx = x - w/2
                dy = y - h/2
                d = math.sqrt(dx*dx + dy*dy)
                angle = math.atan2(dy, dx)
                offset = amplitude * math.sin(d * frequency * 2 * math.pi)
                nx = x + offset * math.cos(angle)
                ny = y + offset * math.sin(angle)
                sx, sy = int(nx), int(ny)
                if 0 <= sx < w and 0 <= sy < h:
                    result[y, x] = img[sy, sx]

        return Image.fromarray(result)


class EditingPipeline:
    def __init__(self):
        self.editor = ImageEditor()
        self.history = []
        self.history_index = -1
        self.current_image = None

    def load_image(self, image):
        self.current_image = image.copy() if image else None
        self.history = []
        self.history_index = -1
        self._save_state()

    def _save_state(self):
        if self.current_image:
            self.history = self.history[:self.history_index + 1]
            self.history.append(self.current_image.copy())
            self.history_index = len(self.history) - 1
            if len(self.history) > 50:
                self.history.pop(0)
                self.history_index -= 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_image = self.history[self.history_index].copy()
        return self.current_image

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_image = self.history[self.history_index].copy()
        return self.current_image

    def can_undo(self):
        return self.history_index > 0

    def can_redo(self):
        return self.history_index < len(self.history) - 1

    def apply(self, operation, params=None):
        if self.current_image is None:
            return None

        if params is None:
            params = {}

        img = self.current_image

        if operation == 'filter':
            img = self.editor.apply_filter(img, params.get('filter_type', 'blur'), params)
        elif operation == 'adjust':
            img = self.editor.adjust(img, params.get('adjustment_type', 'brightness'),
                                     params.get('value', 1.0))
        elif operation == 'transform':
            img = self.editor.transform(img, params.get('transform_type', 'resize'), params)
        elif operation == 'text':
            img = self.editor.draw_text(img, params)
        elif operation == 'shape':
            img = self.editor.draw_shape(img, params)
        elif operation == 'gradient_map':
            colors = params.get('colors', [(0,0,0), (255,255,255)])
            img = self.editor.apply_gradient_map(img, colors)
        elif operation == 'channel_mixer':
            r = params.get('red', (1, 0, 0))
            g = params.get('green', (0, 1, 0))
            b = params.get('blue', (0, 0, 1))
            img = self.editor.channel_mixer(img, r, g, b)
        elif operation == 'color_balance':
            img = self.editor.color_balance(img,
                                            params.get('shadows', (0, 0, 0)),
                                            params.get('midtones', (0, 0, 0)),
                                            params.get('highlights', (0, 0, 0)))
        elif operation == 'lens_flare':
            img = self.editor.lens_flare(img, params.get('x'), params.get('y'),
                                         params.get('brightness', 0.5))
        elif operation == 'kaleidoscope':
            img = self.editor.kaleidoscope(img, int(params.get('segments', 8)))
        elif operation == 'wave_distort':
            img = self.editor.wave_distort(img, float(params.get('amplitude', 10)),
                                           float(params.get('frequency', 0.05)),
                                           params.get('direction', 'horizontal'))
        elif operation == 'buldge':
            img = self.editor.buldge(img, float(params.get('strength', 1.0)))
        elif operation == 'ripple':
            img = self.editor.ripple(img, float(params.get('amplitude', 10)),
                                     float(params.get('frequency', 0.05)))
        else:
            return self.current_image

        self.current_image = img
        self._save_state()
        return self.current_image

    def get_current_image(self):
        return self.current_image

    def resize_canvas(self, width, height, bg_color=(0, 0, 0)):
        if self.current_image is None:
            return None
        new_img = Image.new('RGB', (int(width), int(height)), bg_color)
        new_img.paste(self.current_image, (0, 0))
        self.current_image = new_img
        self._save_state()
        return self.current_image

    def reset(self):
        self.history = []
        self.history_index = -1
        self.current_image = None
