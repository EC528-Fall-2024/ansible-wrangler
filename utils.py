import torch

def check_gpu_availability():
    """
    Check if the system has a GPU available.

    Returns:
        bool: True if a GPU is available, False otherwise.
        str: Details about the GPU or the reason for no GPU.
    """
    if torch.cuda.is_available():
        num_gpus = torch.cuda.device_count()
        gpu_names = [torch.cuda.get_device_name(i) for i in range(num_gpus)]
        return True
    else:
        return False


