from copy import deepcopy
import datetime
from typing import Any, Callable

from ultralytics.utils.plotting import Annotator


def plot(
    img: Any,
    boxes,
    cam_ts: float,
    labels: list[str],
    conf=True,
    line_width=None,
    font_size=None,
    font="Arial.ttf"
):
    """
    Plots the detection results on an input RGB image. Accepts a numpy array (cv2) or a PIL Image.

    Args:
        conf (bool): Whether to plot the detection confidence score.
        line_width (float, optional): The line width of the bounding boxes. If None, it is scaled to the image size.
        font_size (float, optional): The font size of the text. If None, it is scaled to the image size.
        font (str): The font to use for the text.
        pil (bool): Whether to return the image as a PIL Image.
        img (numpy.ndarray): Plot to another image. if not, plot to original image.
        im_gpu (torch.Tensor): Normalized image in gpu with shape (1, 3, 640, 640), for faster mask plotting.
        kpt_radius (int, optional): Radius of the drawn keypoints. Default is 5.
        kpt_line (bool): Whether to draw lines connecting keypoints.
        labels (bool): Whether to plot the label of bounding boxes.
        boxes (bool): Whether to plot the bounding boxes.
        masks (bool): Whether to plot the masks.
        probs (bool): Whether to plot classification probability

    Returns:
        (numpy.ndarray): A numpy array of the annotated image.

    Example:
        ```python
        from PIL import Image
        from vendors.ultralytics import YOLO

        model = YOLO('yolov8n.pt')
        results = model('bus.jpg')  # results list
        for r in results:
            im_array = r.plot()  # plot a BGR numpy array of predictions
            im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
            im.show()  # show image
            im.save('results.jpg')  # save image
        ```
    """

    annotator = Annotator(
        deepcopy(img),
        line_width,
        font_size,
        font,
        pil=False,  # Classify tasks default to pil=True
        example="",
    )

    # Plot Track results
    if boxes is not None:
        for t in boxes:
            d = t
            conf, id = d.conf[0], d.id[0]
            name = "" if id is None else f"id:{int(id)} {labels[int(d.cls)]}"
            label = f"{name} {int(conf* 100)}%" if conf else name
            annotator.box_label(d.xyxy[0], label, color=(0, 225, 27))

    annotator.text_label((544,460,640,480), datetime.datetime.fromtimestamp(cam_ts/1000).strftime('%H:%M:%S'), color=(0,0,0))

    return annotator.result()
