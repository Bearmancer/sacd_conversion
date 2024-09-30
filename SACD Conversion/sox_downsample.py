import shutil, subprocess, sys
from pathlib import Path
from misc import log_to_file

def sox_downsample(path: Path):
    original = path / "original"
    converted = path / "converted"
    problem_files = []

    original.mkdir(exist_ok=True)
    converted.mkdir(exist_ok=True)

    for file in path.glob('*.flac'):
        flac_info = subprocess.run(['sox', '--i', str(file)], capture_output=True, text=True)
        flac_info_output = flac_info.stdout.strip()

        precision_match = [line for line in flac_info_output.splitlines() if "Precision" in line]
        precision = precision_match[0].split(":")[-1].strip() if precision_match else None

        sample_rate_match = [line for line in flac_info_output.splitlines() if "Sample Rate" in line]
        sample_rate = sample_rate_match[0].split(":")[-1].strip() if precision_match else None

        if precision is None or sample_rate is None:
            continue

        actions = {
            "24-bit, 192000": lambda: subprocess.run(['sox', '-S', str(file), '-R', '-G', '-b', '16', str(converted / file.name), 'rate', '-v', '-L', '48000', 'dither']),
            "24-bit, 96000": lambda: subprocess.run(['sox', '-S', str(file), '-R', '-G', '-b', '16', str(converted / file.name), 'rate', '-v', '-L', '48000', 'dither']),
            "24-bit, 48000": lambda: subprocess.run(['sox', '-S', str(file), '-R', '-G', '-b', '16', str(converted / file.name), 'dither']),
            "24-bit, 176400": lambda: subprocess.run(['sox', '-S', str(file), '-R', '-G', '-b', '16', str(converted / file.name), 'rate', '-v', '-L', '44100', 'dither']),
            "24-bit, 88200": lambda: subprocess.run(['sox', '-S', str(file), '-R', '-G', '-b', '16', str(converted / file.name), 'rate', '-v', '-L', '44100', 'dither']),
            "24-bit, 44100": lambda: subprocess.run(['sox', '-S', str(file), '-R', '-G', '-b', '16', str(converted / file.name), 'dither']),
            "16-bit, 48000": lambda: shutil.copy(file, converted / file.name),
            "16-bit, 44100": lambda: shutil.copy(file, converted / file.name)
        }
        action = actions.get(f"{precision}, {sample_rate}")

        if action:
            action()
            file.rename(original / file.name)

        else:
            log_to_file(f"No action found for {file} - Bit Depth: {precision}, Sample Rate: {sample_rate}")
            problem_files.append(file)

    if problem_files:
        log_to_file("The following files' bit-depth and sample rate could not be converted:")
        for problem_file in problem_files:
            log_to_file(f"{problem_file}")

    for converted_file in converted.iterdir():
        converted_file.rename(path / converted_file.name)

    if len(list(path.glob('*.flac'))) == len(list(original.glob('*.flac'))):
        for dir_path in [converted, original]:
            shutil.rmtree(dir_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: script.py <root_dir>")
        sys.exit(1)

    directory = Path(sys.argv[1])
    sox_downsample(directory)