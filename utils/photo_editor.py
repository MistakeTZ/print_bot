from PIL import Image, ImageOps
from fpdf import FPDF
import os

def combine_images_to_pdf(directory, image_paths, output_pdf, page_size=(210, 297), grid_size=(1, 1), grayscale=False, border=5, size=None):
    """
    Объединяет изображения в PDF.
    
    :param image_paths: Список путей к изображениям.
    :param output_pdf: Имя выходного PDF-файла.
    :param page_size: Размер страницы в мм (по умолчанию A4).
    :param grid_size: Сетка для размещения изображений (количество строк и столбцов).
    :param grayscale: Если True, применяет фильтр оттенков серого.
    :param size: Если None, не влияет, если tuple(float, float), устанавливает размер одного фото.
    """
    temp_file_dir = os.path.join(directory, "pages")
    temp_file_pathes = []
    if not os.path.exists(temp_file_dir):
        os.mkdir(temp_file_dir)
    else:
        for filename in os.listdir(temp_file_dir):
            file_path = os.path.join(temp_file_dir, filename)
            os.remove(file_path)

    image_paths = [image_path for image_path in image_paths if image_path.endswith(".jpg")]

    on_page = grid_size[0] * grid_size[1]
    mm_to_px = 11.81  # 1 мм в пикселях при 300 DPI
    page_width, page_height = (int(page_size[0] * mm_to_px), int(page_size[1] * mm_to_px))

    spaces_count = (grid_size[0] + 1, grid_size[1] + 1)
    if size:
        cell_width = size[0] * mm_to_px
        cell_height = size[1] * mm_to_px
        spaces = ((page_width - cell_width * grid_size[1]) / (grid_size[1] + 1),
                  (page_height - cell_height * grid_size[0]) / (grid_size[0] + 1))
        borders = [int(space / mm_to_px) for space in spaces]

    else:
        spaces = (border * mm_to_px, border * mm_to_px)
        spaces_count = (grid_size[0] + 1, grid_size[1] + 1)

        cell_width = int((page_width - spaces[1] * spaces_count[1]) // grid_size[1])
        cell_height = int((page_height - spaces[0] * spaces_count[0]) // grid_size[0])
        borders = [border] * 2
    
    pdf = FPDF(unit="mm", format=page_size)
    pdf.set_auto_page_break(auto=True, margin=0)
    
    for i in range(0, len(image_paths), on_page):
        sheet = Image.new("RGB", (page_width, page_height), "white")
        for idx in range(min(on_page, len(image_paths) - i)):
            img = Image.open(os.path.join(directory, image_paths[i + idx]))

            if grayscale:
                img = ImageOps.grayscale(img).convert("RGB")

            size = img.size

            width, height, is_rotate, offsets = count_width_and_height(cell_width, cell_height, *size)
            if is_rotate:
                img = img.rotate(90, expand=True)

            img = img.resize((width, height), Image.Resampling.LANCZOS)
            x = int((idx % grid_size[0]) * (cell_width + spaces[0]) + spaces[0]) + offsets[0]
            y = int((idx // grid_size[1]) * (cell_height + spaces[1]) + spaces[1]) + offsets[1]
            sheet.paste(img, (x, y))

        temp_file_path = os.path.join(temp_file_dir, str(i) + ".jpg")
        temp_file_pathes.append(temp_file_path)
        sheet.save(temp_file_path, format="JPEG")
        
        # Добавляем страницу в PDF
        pdf.add_page()
        pdf.image(temp_file_path, x=0, y=0, w=page_size[0], h=page_size[1])

    output_pdf = os.path.join(directory, output_pdf)
    pdf.output(output_pdf)
    print(f"PDF создан {output_pdf}")

    return_values = {
        # "output": output_pdf,
        "pathes": temp_file_pathes,
        "sizes": (cell_width / mm_to_px, cell_height / mm_to_px),
        "borders": borders
    }
    return return_values


def count_width_and_height(cell_width, cell_height, width, height):
    is_rotate = width > height * 1.2
    if is_rotate:
        temp = height
        height = width
        width = temp

    coefs = (cell_width / width, cell_height / height)
    width = int(width * min(coefs))
    height = int(height * min(coefs))
    offsets = (int((cell_width - width) / 2), int((cell_height - height) / 2))

    return width, height, is_rotate, offsets
