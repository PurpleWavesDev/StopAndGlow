import json 

class Config:
    def __init__(self):
        pass

    def save_config(self, path, name='calibration.yaml'):
        full_path = os.path.join(path, name)
        if not os.path.exists(full_path):
            os.makedirs(full_path)

        with open(full_path, "w") as file:
            file.write("Test\n")
