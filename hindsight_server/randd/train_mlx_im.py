import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlxim.model import create_model
from mlxim.data import LabelFolderDataset, DataLoader

train_dataset = LabelFolderDataset(
    root_dir="../testing_data/screenshot_clusters/Messages_kb",
    class_map={0: "keyboard_t", 1: "no_keyboard_t"}
)
train_loader = DataLoader(
    dataset=train_dataset,
    batch_size=4,
    shuffle=True,
    num_workers=4
)
model = create_model("resnet18") # pretrained weights loaded from HF
optimizer = optim.Adam(learning_rate=1e-3)

def train_step(model, inputs, target):
    logits = model(inputs)
    loss = mx.mean(nn.losses.cross_entropy(logits, target))
    return loss

model.train()
for epoch in range(1):
    for batch in train_loader:
        x, target = batch
        x = x.astype(mx.float32) / 255.0
        train_step_fn = nn.value_and_grad(model, train_step)
        loss, grads = train_step_fn(model, x, target)
        optimizer.update(model, grads)
        mx.eval(model.state, optimizer.state)
        
model.save_weights("keyboard_pred.npz")