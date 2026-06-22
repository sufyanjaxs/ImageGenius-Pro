import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import colorsys
import math
import random
import struct
import io


class ProceduralGenerator:

    @staticmethod
    def mandelbrot(width, height, x_min=-2.5, x_max=1.5, y_min=-1.5, y_max=1.5, max_iter=256, power=2, coloring='spectral', julia=False, julia_c=(-0.7, 0.27)):
        img = np.zeros((height, width, 3), dtype=np.uint8)
        x_step = (x_max - x_min) / width
        y_step = (y_max - y_min) / height

        for py in range(height):
            for px in range(width):
                x = x_min + px * x_step
                y = y_min + py * y_step

                if julia:
                    zx, zy = x, y
                    cx, cy = julia_c
                else:
                    zx, zy = 0.0, 0.0
                    cx, cy = x, y

                iteration = 0
                while zx * zx + zy * zy < 4 and iteration < max_iter:
                    if power == 2:
                        zx_new = zx * zx - zy * zy + cx
                        zy_new = 2 * zx * zy + cy
                    elif power == 3:
                        zx_new = zx * zx * zx - 3 * zx * zy * zy + cx
                        zy_new = 3 * zx * zx * zy - zy * zy * zy + cy
                    elif power == 4:
                        zx_new = zx*zx*zx*zx - 6*zx*zx*zy*zy + zy*zy*zy*zy + cx
                        zy_new = 4*zx*zx*zx*zy - 4*zx*zy*zy*zy + cy
                    else:
                        r = (zx*zx + zy*zy) ** (power/2)
                        theta = power * math.atan2(zy, zx)
                        zx_new = r * math.cos(theta) + cx
                        zy_new = r * math.sin(theta) + cy

                    if zx == zx_new and zy == zy_new:
                        iteration = max_iter
                        break
                    zx, zy = zx_new, zy_new
                    iteration += 1

                if iteration == max_iter:
                    r, g, b = 0, 0, 0
                else:
                    smooth = iteration + 1 - math.log2(math.log2(zx*zx + zy*zy + 1e-10)) if zx*zx + zy*zy > 0 else iteration
                    t = smooth / max_iter

                    if coloring == 'spectral':
                        r = int(255 * (0.5 + 0.5 * math.sin(2 * math.pi * t * 1.5)))
                        g = int(255 * (0.5 + 0.5 * math.sin(2 * math.pi * t * 2.5 + 0.33)))
                        b = int(255 * (0.5 + 0.5 * math.sin(2 * math.pi * t * 3.5 + 0.67)))
                    elif coloring == 'fire':
                        r = min(255, int(255 * t * 3))
                        g = min(255, int(255 * (t * 3 - 1)))
                        b = min(255, int(255 * (t * 3 - 2)))
                    elif coloring == 'ocean':
                        r = int(255 * (1 - t) * 0.2)
                        g = int(255 * (0.3 + 0.7 * math.sin(t * math.pi)))
                        b = int(255 * (0.5 + 0.5 * math.sin(t * math.pi * 2)))
                    elif coloring == 'neon':
                        r = int(255 * (0.5 + 0.5 * math.sin(t * 12 + 0)))
                        g = int(255 * (0.5 + 0.5 * math.sin(t * 12 + 2.1)))
                        b = int(255 * (0.5 + 0.5 * math.sin(t * 12 + 4.2)))
                    elif coloring == 'gray':
                        v = int(255 * t)
                        r, g, b = v, v, v
                    else:
                        r = int(255 * t)
                        g = int(255 * t * 0.5)
                        b = int(255 * (1 - t))

                img[py, px] = [r, g, b]

        return Image.fromarray(img, 'RGB')

    @staticmethod
    def perlin_noise(width, height, scale=50, octaves=6, seed=None, color_mode='colorful'):
        if seed is not None:
            random.seed(seed)

        def generate_perlin(width, height, scale):
            def fade(t):
                return t * t * t * (t * (t * 6 - 15) + 10)

            def lerp(a, b, t):
                return a + t * (b - a)

            def gradient(h, x, y):
                vectors = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                v = vectors[h % 4]
                return v[0] * x + v[1] * y

            permutation = list(range(512))
            random.shuffle(permutation)
            p = permutation * 2

            output = np.zeros((height, width), dtype=np.float64)

            for i in range(height):
                for j in range(width):
                    x = j / scale
                    y = i / scale
                    xi = int(x) % 256
                    yi = int(y) % 256
                    xf = x - int(x)
                    yf = y - int(y)

                    u = fade(xf)
                    v = fade(yf)

                    aa = p[p[xi] + yi]
                    ab = p[p[xi] + yi + 1]
                    ba = p[p[xi + 1] + yi]
                    bb = p[p[xi + 1] + yi + 1]

                    x1 = lerp(gradient(aa, xf, yf), gradient(ba, xf - 1, yf), u)
                    x2 = lerp(gradient(ab, xf, yf - 1), gradient(bb, xf - 1, yf - 1), u)
                    output[i, j] = lerp(x1, x2, v)

            return output

        noise = np.zeros((height, width), dtype=np.float64)
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for octave in range(octaves):
            current_scale = scale / frequency
            n = generate_perlin(width, height, current_scale) * amplitude
            noise += n
            max_value += amplitude
            amplitude *= 0.5
            frequency *= 2.0

        noise = noise / max_value

        if color_mode == 'colorful':
            r = np.zeros((height, width), dtype=np.uint8)
            g = np.zeros((height, width), dtype=np.uint8)
            b = np.zeros((height, width), dtype=np.uint8)

            for i in range(height):
                for j in range(width):
                    val = noise[i, j]
                    r_val = int(255 * (0.5 + 0.5 * math.sin(val * 4 + 0)))
                    g_val = int(255 * (0.5 + 0.5 * math.sin(val * 4 + 2.1)))
                    b_val = int(255 * (0.5 + 0.5 * math.sin(val * 4 + 4.2)))
                    r[i, j] = max(0, min(255, r_val))
                    g[i, j] = max(0, min(255, g_val))
                    b[i, j] = max(0, min(255, b_val))

            return Image.fromarray(np.stack([r, g, b], axis=2), 'RGB')

        elif color_mode == 'terrain':
            img = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(height):
                for j in range(width):
                    val = (noise[i, j] + 1) * 0.5
                    if val < 0.3:
                        c = (int(50 + val * 100), int(80 + val * 100), int(150))
                    elif val < 0.5:
                        c = (int(100 + (val - 0.3) * 300), int(150 + (val - 0.3) * 200), int(50))
                    elif val < 0.7:
                        c = (int(100 + (val - 0.5) * 200), int(130 + (val - 0.5) * 100), int(30))
                    elif val < 0.85:
                        c = (int(120 + (val - 0.7) * 300), int(100 + (val - 0.7) * 100), int(60))
                    else:
                        c = (int(240), int(240), int(240))
                    img[i, j] = [max(0, min(255, c[0])), max(0, min(255, c[1])), max(0, min(255, c[2]))]
            return Image.fromarray(img, 'RGB')

        elif color_mode == 'cloud':
            img = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(height):
                for j in range(width):
                    v = int(255 * ((noise[i, j] + 1) * 0.5))
                    v = max(0, min(255, v))
                    img[i, j] = [v, v, v + int(v * 0.3)]
            return Image.fromarray(img, 'RGB')

        elif color_mode == 'lava':
            img = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(height):
                for j in range(width):
                    val = (noise[i, j] + 1) * 0.5
                    r = min(255, int(255 * val * 2))
                    g = min(255, int(255 * max(0, val * 3 - 1)))
                    b = min(255, int(255 * max(0, val * 4 - 3)))
                    img[i, j] = [r, g, b]
            return Image.fromarray(img, 'RGB')

        else:
            img = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(height):
                for j in range(width):
                    v = int(255 * ((noise[i, j] + 1) * 0.5))
                    v = max(0, min(255, v))
                    img[i, j] = [v, v, v]
            return Image.fromarray(img, 'RGB')

    @staticmethod
    def plasma(width, height, roughness=0.7, seed=None, color_scheme='plasma'):
        if seed is not None:
            random.seed(seed)

        size = 1
        while size < max(width, height):
            size *= 2

        grid = [[0.0] * (size + 1) for _ in range(size + 1)]
        grid[0][0] = random.random()
        grid[0][size] = random.random()
        grid[size][0] = random.random()
        grid[size][size] = random.random()

        step = size
        while step > 1:
            half = step // 2
            rough = roughness * (step / size)

            for x in range(0, size, step):
                for y in range(0, size, step):
                    avg = (grid[x][y] + grid[x + step][y] + grid[x][y + step] + grid[x + step][y + step]) / 4
                    grid[x + half][y + half] = avg + (random.random() - 0.5) * rough

            for x in range(0, size + 1, half):
                for y in range(0, size + 1, half):
                    if (x + half) <= size and (y % step == 0):
                        if grid[x + half][y] == 0.0:
                            avg = (grid[x][y] + grid[x + step][y]) / 2 if x + step <= size else grid[x][y]
                            if (x - half) >= 0:
                                avg = (avg + grid[x - half][y]) / 2
                            grid[x + half][y] = avg + (random.random() - 0.5) * rough
                    if (y + half) <= size and (x % step == 0):
                        if grid[x][y + half] == 0.0:
                            avg = (grid[x][y] + grid[x][y + step]) / 2 if y + step <= size else grid[x][y]
                            if (y - half) >= 0:
                                avg = (avg + grid[x][y - half]) / 2
                            grid[x][y + half] = avg + (random.random() - 0.5) * rough

            step = half

        noise_min = min(min(row) for row in grid)
        noise_max = max(max(row) for row in grid)
        noise_range = noise_max - noise_min
        if noise_range == 0:
            noise_range = 1

        img = np.zeros((height, width, 3), dtype=np.uint8)

        for y in range(height):
            for x in range(width):
                gx = int(x * size / width)
                gy = int(y * size / height)
                val = (grid[gx][gy] - noise_min) / noise_range

                if color_scheme == 'plasma':
                    r = int(255 * (0.5 + 0.5 * math.sin(val * 12 + 0)))
                    g = int(255 * (0.5 + 0.5 * math.sin(val * 12 + 2.1)))
                    b = int(255 * (0.5 + 0.5 * math.sin(val * 12 + 4.2)))
                elif color_scheme == 'fire':
                    r = int(255 * min(1, val * 3))
                    g = int(255 * max(0, min(1, val * 3 - 0.5)))
                    b = int(255 * max(0, min(1, val * 3 - 1.5)))
                elif color_scheme == 'underwater':
                    r = int(255 * val * 0.3)
                    g = int(255 * (0.3 + 0.7 * val))
                    b = int(255 * (0.5 + 0.5 * val))
                elif color_scheme == 'sunset':
                    r = int(255 * (0.8 + 0.2 * math.sin(val * 8)))
                    g = int(255 * (0.3 + 0.5 * math.sin(val * 8 + 2)))
                    b = int(255 * (0.2 + 0.3 * math.sin(val * 8 + 4)))
                else:
                    v = int(255 * val)
                    r, g, b = v, v, v

                img[y, x] = [max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))]

        return Image.fromarray(img, 'RGB')

    @staticmethod
    def cellular_automata(width, height, generations=50, rule=110, symmetric=False):
        def rule_binary(num):
            return [(num >> i) & 1 for i in range(8)]

        rules = rule_binary(rule)
        size = width
        grid = np.zeros((generations, size), dtype=np.uint8)

        if symmetric:
            grid[0, size // 2] = 1
        else:
            grid[0, random.randint(size // 4, 3 * size // 4)] = 1

        for gen in range(1, generations):
            for cell in range(size):
                left = grid[gen - 1, (cell - 1) % size]
                center = grid[gen - 1, cell]
                right = grid[gen - 1, (cell + 1) % size]
                idx = 7 - (left << 2 | center << 1 | right)
                grid[gen, cell] = rules[idx]

        img = np.zeros((generations, size, 3), dtype=np.uint8)
        for y in range(generations):
            for x in range(size):
                if grid[y, x]:
                    t = 1 - y / generations
                    r = int(255 * (0.5 + 0.5 * math.sin(t * 3)))
                    g = int(255 * (0.5 + 0.5 * math.sin(t * 3 + 2)))
                    b = int(255 * (0.5 + 0.5 * math.sin(t * 3 + 4)))
                    img[y, x] = [r, g, b]

        return Image.fromarray(img, 'RGB').resize((width, height), Image.NEAREST)

    @staticmethod
    def game_of_life(width, height, generations=100, seed_density=0.3, cell_size=4):
        w = width // cell_size
        h = height // cell_size

        grid = np.random.random((h, w)) < seed_density

        def step(g):
            n = np.zeros_like(g)
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    n += np.roll(np.roll(g, dy, axis=0), dx, axis=1)
            return (n == 3) | ((g) & (n == 2))

        frames = []
        for _ in range(generations):
            img = np.zeros((h, w, 3), dtype=np.uint8)
            for y in range(h):
                for x in range(w):
                    if grid[y, x]:
                        intensity = 1.0 - (_ / generations) * 0.5
                        r = int(255 * intensity)
                        g = int(255 * intensity * 0.5 + 128 * intensity)
                        b = int(255 * intensity)
                        img[y, x] = [r, g, b]
            frames.append(Image.fromarray(img, 'RGB').resize((width, height), Image.NEAREST))
            grid = step(grid)

        return frames

    @staticmethod
    def gradient(width, height, colors, style='linear', angle=0, center=None):
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)

        if len(colors) < 2:
            colors = [(0, 0, 0), (255, 255, 255)]

        for y in range(height):
            for x in range(width):
                if style == 'linear':
                    rad = math.radians(angle)
                    nx = x / width
                    ny = y / height
                    t = nx * math.cos(rad) + ny * math.sin(rad)
                    t = (t + 1) / 2
                elif style == 'radial':
                    cx = center[0] if center else width / 2
                    cy = center[1] if center else height / 2
                    dx = x - cx
                    dy = y - cy
                    t = math.sqrt(dx*dx + dy*dy) / math.sqrt(cx*cx + cy*cy)
                elif style == 'angular':
                    cx = center[0] if center else width / 2
                    cy = center[1] if center else height / 2
                    t = math.atan2(y - cy, x - cx) / (2 * math.pi) + 0.5
                elif style == 'diamond':
                    cx = center[0] if center else width / 2
                    cy = center[1] if center else height / 2
                    t = (abs(x - cx) + abs(y - cy)) / (cx + cy)
                else:
                    t = x / width

                t = max(0.0, min(1.0, t))

                segments = len(colors) - 1
                seg = t * segments
                idx = min(int(seg), segments - 1)
                local_t = seg - idx

                c1 = colors[idx]
                c2 = colors[min(idx + 1, segments)]
                r = int(c1[0] + (c2[0] - c1[0]) * local_t)
                g = int(c1[1] + (c2[1] - c1[1]) * local_t)
                b = int(c1[2] + (c2[2] - c1[2]) * local_t)

                draw.point((x, y), fill=(r, g, b))

        return img

    @staticmethod
    def geometric_pattern(width, height, pattern_type='circles', scale=50, density=0.8, rotation=0, color1=(255, 100, 50), color2=(50, 100, 255), bg=(10, 10, 20)):
        img = Image.new('RGB', (width, height), bg)
        draw = ImageDraw.Draw(img)

        rows = max(1, int(height / scale * density))
        cols = max(1, int(width / scale * density))

        rad = math.radians(rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        for row in range(rows):
            for col in range(cols):
                cx = col * (width / cols) + (width / cols) / 2
                cy = row * (height / rows) + (height / rows) / 2

                rx = cx * cos_r - cy * sin_r + width / 2
                ry = cx * sin_r + cy * cos_r + height / 2

                t = (row / rows + col / cols) * 0.5
                t_r = int(color1[0] + (color2[0] - color1[0]) * t)
                t_g = int(color1[1] + (color2[1] - color1[1]) * t)
                t_b = int(color1[2] + (color2[2] - color1[2]) * t)
                color = (max(0, min(255, t_r)), max(0, min(255, t_g)), max(0, min(255, t_b)))

                s = scale * 0.4

                if pattern_type == 'circles':
                    draw.ellipse([rx - s, ry - s, rx + s, ry + s], outline=color, width=1)
                    fill_c = (color[0] // 4, color[1] // 4, color[2] // 4)
                    draw.ellipse([rx - s * 0.6, ry - s * 0.6, rx + s * 0.6, ry + s * 0.6], fill=fill_c)

                elif pattern_type == 'squares':
                    draw.rectangle([rx - s, ry - s, rx + s, ry + s], outline=color, width=1)
                    draw.rectangle([rx - s * 0.6, ry - s * 0.6, rx + s * 0.6, ry + s * 0.6], fill=(color[0] // 4, color[1] // 4, color[2] // 4))

                elif pattern_type == 'triangles':
                    pts = [(rx, ry - s), (rx - s * 0.866, ry + s * 0.5), (rx + s * 0.866, ry + s * 0.5)]
                    draw.polygon(pts, outline=color, width=1)

                elif pattern_type == 'hexagons':
                    pts = []
                    for i in range(6):
                        a = math.radians(60 * i - 30)
                        pts.append((rx + s * math.cos(a), ry + s * math.sin(a)))
                    draw.polygon(pts, outline=color, width=1)

                elif pattern_type == 'stars':
                    pts = []
                    for i in range(10):
                        a = math.radians(36 * i - 90)
                        r = s if i % 2 == 0 else s * 0.4
                        pts.append((rx + r * math.cos(a), ry + r * math.sin(a)))
                    draw.polygon(pts, outline=color, width=1)

                elif pattern_type == 'waves':
                    for x in range(int(rx - s), int(rx + s)):
                        if 0 <= x < width:
                            yy = ry + math.sin((x - rx) / s * math.pi * 3) * s * 0.5
                            if 0 <= yy < height:
                                draw.point((x, yy), fill=color)
                    draw.ellipse([rx - 2, ry - 2, rx + 2, ry + 2], fill=color)

        return img

    @staticmethod
    def spirograph(width, height, R=100, r=50, d=30, num_points=10000, color=(255, 100, 200), bg=(10, 10, 20)):
        img = Image.new('RGB', (width, height), bg)
        draw = ImageDraw.Draw(img)

        cx, cy = width / 2, height / 2
        scale = min(width, height) / (2 * (R + r))

        t = 0
        step = 2 * math.pi * r / (R * num_points) if R > 0 else 0.001

        prev_x = None
        prev_y = None

        gcd_val = math.gcd(int(R), int(r)) if R > 0 and r > 0 else 1
        max_t = 2 * math.pi * (r // gcd_val) if r > 0 else 2 * math.pi

        while t < max_t * 3:
            x = cx + scale * ((R + r) * math.cos(t) - d * math.cos(((R + r) / r) * t if r != 0 else t))
            y = cy + scale * ((R + r) * math.sin(t) - d * math.sin(((R + r) / r) * t if r != 0 else t))

            if prev_x is not None and prev_y is not None:
                t_norm = t / max_t
                r_c = int(color[0] * (0.5 + 0.5 * math.sin(t_norm * 8)))
                g_c = int(color[1] * (0.5 + 0.5 * math.sin(t_norm * 8 + 2)))
                b_c = int(color[2] * (0.5 + 0.5 * math.sin(t_norm * 8 + 4)))
                line_color = (max(0, min(255, r_c)), max(0, min(255, g_c)), max(0, min(255, b_c)))
                draw.line([(prev_x, prev_y), (x, y)], fill=line_color, width=1)

            prev_x, prev_y = x, y
            t += step

        return img

    @staticmethod
    def voronoi(width, height, num_points=50, seed=None, color_mode='random'):
        if seed is not None:
            random.seed(seed)

        points = [(random.randint(0, width), random.randint(0, height)) for _ in range(num_points)]

        colors = []
        for _ in range(num_points):
            if color_mode == 'random':
                c = (random.randint(30, 255), random.randint(30, 255), random.randint(30, 255))
            elif color_mode == 'pastel':
                c = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255))
            elif color_mode == 'dark':
                c = (random.randint(20, 120), random.randint(20, 120), random.randint(20, 120))
            else:
                hue = random.random()
                rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
                c = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            colors.append(c)

        img = np.zeros((height, width, 3), dtype=np.uint8)
        dist_map = np.full((height, width), float('inf'))
        nearest = np.zeros((height, width), dtype=np.int32)

        points_y = np.array([p[1] for p in points])
        points_x = np.array([p[0] for p in points])

        for i, (px, py) in enumerate(points):
            y_indices, x_indices = np.ogrid[:height, :width]
            dists = (y_indices - py) ** 2 + (x_indices - px) ** 2
            mask = dists < dist_map
            dist_map[mask] = dists[mask]
            nearest[mask] = i

        for y in range(height):
            for x in range(width):
                idx = nearest[y, x]
                img[y, x] = colors[idx]

        return Image.fromarray(img, 'RGB')

    @staticmethod
    def galaxy(width, height, num_stars=3000, spiral_arms=3, seed=None, bg=(5, 5, 15)):
        if seed is not None:
            random.seed(seed)

        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:, :] = bg

        cx, cy = width / 2, height / 2

        star_colors = [
            (200, 200, 255),
            (255, 255, 255),
            (255, 200, 150),
            (255, 150, 100),
            (150, 200, 255),
            (255, 220, 180),
        ]

        for _ in range(num_stars):
            arm = random.randint(0, spiral_arms - 1)
            arm_angle = (arm / spiral_arms) * 2 * math.pi

            dist_factor = random.random() ** 0.5
            angle = arm_angle + dist_factor * 4 * math.pi

            spread = random.gauss(0, 15 * (1 + dist_factor))
            sx = cx + dist_factor * cx * 0.9 * math.cos(angle) + spread
            sy = cy + dist_factor * cy * 0.9 * math.sin(angle) + spread * 0.5

            if 0 <= sx < width and 0 <= sy < height:
                brightness = 1.0 - dist_factor * 0.7
                color = random.choice(star_colors)
                size = int(1 + random.random() * 3 * brightness)
                r = int(color[0] * brightness)
                g = int(color[1] * brightness)
                b = int(color[2] * brightness)
                r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))

                for dy in range(-size, size + 1):
                    for dx in range(-size, size + 1):
                        if dx * dx + dy * dy <= size * size:
                            sx2, sy2 = int(sx + dx), int(sy + dy)
                            if 0 <= sx2 < width and 0 <= sy2 < height:
                                if random.random() < 0.8:
                                    img[sy2, sx2] = [r, g, b]

        core_size = int(min(width, height) * 0.08)
        for y in range(max(0, int(cy) - core_size), min(height, int(cy) + core_size)):
            for x in range(max(0, int(cx) - core_size), min(width, int(cx) + core_size)):
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / core_size
                if d < 1:
                    intensity = int(255 * (1 - d) * 0.8)
                    if intensity > img[y, x, 0]:
                        img[y, x] = [intensity, intensity, int(intensity * 0.8)]

        return Image.fromarray(img, 'RGB')

    @staticmethod
    def wave_pattern(width, height, freq=0.05, amplitude=50, color1=(0, 100, 255), color2=(255, 50, 100), bg=(5, 5, 20), wave_type='sine'):
        img = np.zeros((height, width, 3), dtype=np.uint8)

        for y in range(height):
            for x in range(width):
                if wave_type == 'sine':
                    offset = amplitude * math.sin(x * freq) * math.sin(y * freq * 0.5)
                elif wave_type == 'cosine':
                    offset = amplitude * math.cos(x * freq) * math.cos(y * freq * 0.5)
                elif wave_type == 'tangent':
                    offset = amplitude * math.tan((x % int(1/freq)) * freq * 0.5)
                elif wave_type == 'square_wave':
                    offset = amplitude if int(x * freq) % 2 == 0 else -amplitude
                elif wave_type == 'triangle':
                    t = (x * freq) % 1
                    offset = amplitude * (2 * abs(2 * t - 1) - 1)
                elif wave_type == 'sawtooth':
                    t = (x * freq) % 1
                    offset = amplitude * (2 * t - 1)

                r = int(abs(offset) / amplitude * color1[0] + (1 - abs(offset) / amplitude) * color2[0])
                g = int(abs(offset) / amplitude * color1[1] + (1 - abs(offset) / amplitude) * color2[1])
                b = int(abs(offset) / amplitude * color1[2] + (1 - abs(offset) / amplitude) * color2[2])

                r = max(bg[0], min(255, r))
                g = max(bg[1], min(255, g))
                b = max(bg[2], min(255, b))

                img[y, x] = [r, g, b]

        return Image.fromarray(img, 'RGB')

    @staticmethod
    def koch_snowflake(width, height, iterations=4, color=(100, 200, 255), bg=(10, 10, 30)):
        img = Image.new('RGB', (width, height), bg)
        draw = ImageDraw.Draw(img)

        def koch_line(x1, y1, x2, y2, depth):
            if depth == 0:
                draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
                return

            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx*dx + dy*dy) / 3
            angle = math.atan2(dy, dx)

            x3 = x1 + dx / 3
            y3 = y1 + dy / 3
            x4 = x1 + 2 * dx / 3
            y4 = y1 + 2 * dy / 3

            x5 = x3 + length * math.cos(angle + math.pi / 3)
            y5 = y3 + length * math.sin(angle + math.pi / 3)

            koch_line(x1, y1, x3, y3, depth - 1)
            koch_line(x3, y3, x5, y5, depth - 1)
            koch_line(x5, y5, x4, y4, depth - 1)
            koch_line(x4, y4, x2, y2, depth - 1)

        size = min(width, height) * 0.4
        cx, cy = width / 2, height / 2

        p1 = (cx, cy - size)
        p2 = (cx + size * math.cos(math.pi / 6), cy + size * math.sin(math.pi / 6))
        p3 = (cx - size * math.cos(math.pi / 6), cy + size * math.sin(math.pi / 6))

        koch_line(*p1, *p2, iterations)
        koch_line(*p2, *p3, iterations)
        koch_line(*p3, *p1, iterations)

        return img

    @staticmethod
    def abstract_art(width, height, seed=None):
        """Generates abstract art using random brush strokes, curves and shapes"""
        if seed is not None:
            random.seed(seed)

        img = Image.new('RGB', (width, height), (random.randint(5, 25), random.randint(5, 25), random.randint(10, 30)))
        draw = ImageDraw.Draw(img)

        bg_color = img.getpixel((0, 0))

        for _ in range(random.randint(50, 200)):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(10, 200)
            color = (
                random.randint(30, 255),
                random.randint(30, 255),
                random.randint(30, 255)
            )
            alpha = random.randint(30, 120)

            shape_type = random.choice(['circle', 'rect', 'line', 'curve', 'blob'])

            if shape_type == 'circle':
                draw.ellipse([x - size // 2, y - size // 2, x + size // 2, y + size // 2],
                             fill=(*color, alpha) if hasattr(draw, 'alpha') else color)

            elif shape_type == 'rect':
                draw.rectangle([x - size // 2, y - size // 2, x + size // 2, y + size // 2],
                               fill=(*color, alpha) if hasattr(draw, 'alpha') else color)

            elif shape_type == 'line':
                x2 = x + random.randint(-200, 200)
                y2 = y + random.randint(-200, 200)
                draw.line([(x, y), (x2, y2)], fill=color, width=random.randint(1, 10))

            elif shape_type == 'curve':
                points = []
                for _ in range(3):
                    points.append((x + random.randint(-100, 100), y + random.randint(-100, 100)))
                if len(points) >= 3:
                    draw.line(points, fill=color, width=random.randint(1, 8))

            elif shape_type == 'blob':
                pts = []
                num_points = random.randint(6, 12)
                for i in range(num_points):
                    a = 2 * math.pi * i / num_points
                    r = size * (0.5 + 0.5 * random.random())
                    pts.append((x + r * math.cos(a), y + r * math.sin(a)))
                draw.polygon(pts, fill=color)

        return img


class GeneratorPipeline:
    def __init__(self):
        self.gen = ProceduralGenerator()

    def generate(self, params):
        gen_type = params.get('type', 'mandelbrot')
        width = int(params.get('width', 1920))
        height = int(params.get('height', 1080))

        if gen_type == 'mandelbrot':
            return self.gen.mandelbrot(
                width, height,
                x_min=float(params.get('x_min', -2.5)),
                x_max=float(params.get('x_max', 1.5)),
                y_min=float(params.get('y_min', -1.5)),
                y_max=float(params.get('y_max', 1.5)),
                max_iter=int(params.get('max_iter', 256)),
                power=int(params.get('power', 2)),
                coloring=params.get('coloring', 'spectral')
            )

        elif gen_type == 'julia':
            return self.gen.mandelbrot(
                width, height,
                max_iter=int(params.get('max_iter', 256)),
                coloring=params.get('coloring', 'spectral'),
                julia=True,
                julia_c=(float(params.get('julia_cr', -0.7)), float(params.get('julia_ci', 0.27)))
            )

        elif gen_type == 'perlin':
            return self.gen.perlin_noise(
                width, height,
                scale=float(params.get('scale', 50)),
                octaves=int(params.get('octaves', 6)),
                seed=int(params.get('seed', 0)) if params.get('seed') else None,
                color_mode=params.get('color_mode', 'colorful')
            )

        elif gen_type == 'plasma':
            return self.gen.plasma(
                width, height,
                roughness=float(params.get('roughness', 0.7)),
                seed=int(params.get('seed', 0)) if params.get('seed') else None,
                color_scheme=params.get('color_scheme', 'plasma')
            )

        elif gen_type == 'cellular':
            return self.gen.cellular_automata(
                width, height,
                generations=int(params.get('generations', 50)),
                rule=int(params.get('rule', 110)),
                symmetric=params.get('symmetric', 'false').lower() == 'true'
            )

        elif gen_type == 'gradient':
            colors_str = params.get('colors', '#ff0000,#ff8800,#ffff00,#00ff00,#0000ff')
            hex_colors = colors_str.split(',')
            colors = []
            for hc in hex_colors:
                hc = hc.strip().lstrip('#')
                if len(hc) == 6:
                    colors.append(tuple(int(hc[i:i+2], 16) for i in (0, 2, 4)))
            if not colors:
                colors = [(255, 0, 0), (0, 0, 255)]
            return self.gen.gradient(
                width, height,
                colors=colors,
                style=params.get('gradient_style', 'linear'),
                angle=float(params.get('angle', 0)),
                center=(width//2, height//2)
            )

        elif gen_type == 'geometric':
            return self.gen.geometric_pattern(
                width, height,
                pattern_type=params.get('pattern_type', 'circles'),
                scale=float(params.get('pattern_scale', 50)),
                density=float(params.get('density', 0.8)),
                rotation=float(params.get('pattern_rotation', 0))
            )

        elif gen_type == 'spirograph':
            return self.gen.spirograph(
                width, height,
                R=int(params.get('R', 100)),
                r=int(params.get('r', 50)),
                d=int(params.get('d', 30)),
                num_points=int(params.get('num_points', 10000))
            )

        elif gen_type == 'voronoi':
            return self.gen.voronoi(
                width, height,
                num_points=int(params.get('num_points', 50)),
                seed=int(params.get('seed', 0)) if params.get('seed') else None,
                color_mode=params.get('color_mode', 'random')
            )

        elif gen_type == 'galaxy':
            return self.gen.galaxy(
                width, height,
                num_stars=int(params.get('num_stars', 3000)),
                spiral_arms=int(params.get('spiral_arms', 3)),
                seed=int(params.get('seed', 0)) if params.get('seed') else None
            )

        elif gen_type == 'wave':
            return self.gen.wave_pattern(
                width, height,
                freq=float(params.get('freq', 0.05)),
                amplitude=float(params.get('amplitude', 50)),
                wave_type=params.get('wave_type', 'sine')
            )

        elif gen_type == 'snowflake':
            return self.gen.koch_snowflake(
                width, height,
                iterations=int(params.get('iterations', 4))
            )

        elif gen_type == 'abstract':
            return self.gen.abstract_art(
                width, height,
                seed=int(params.get('seed', 0)) if params.get('seed') else None
            )

        else:
            return self.gen.mandelbrot(width, height)
