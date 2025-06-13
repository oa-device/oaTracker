import os
import PIL.Image as Image
from model import CSRNet
import torch
from torchvision import transforms

def load():
    transform=transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    model = CSRNet()

    checkpoint = torch.load('weights.pth', map_location="mps")

    model.load_state_dict(checkpoint)

    return model, transform


def predict_count(model, img_path, transform):
    img = transform(Image.open(img_path).convert('RGB'))
    output = model(img.unsqueeze(0))
    return int(output.detach().cpu().sum().numpy())


if __name__ == "__main__":
    model, transform = load()
    img_path = "img_to_predict.jpg"
    if not os.path.exists(img_path):
        print(f"Image file {img_path} does not exist.")
        exit(1)
    count = predict_count(model, img_path, transform)
    print(f"Predicted count: {count}")
