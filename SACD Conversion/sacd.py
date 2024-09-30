import subprocess, re, sys, unicodedata
from pathlib import Path
from misc import log_to_file
from sox_downsample import sox_downsample

def extract_sacds(path):
    normalized_name = ''.join(c for c in unicodedata.normalize('NFD', path.name) if unicodedata.category(c) != 'Mn')

    path = path.rename(path.with_name(normalized_name)) if normalized_name != path.name else path

    iso_files = path.rglob("*.iso")

    for iso_file in iso_files:
        flac_folder = iso_to_flac(iso_file, path)

        # Disable if user does not intend to downsample to 16-bit
        sox_downsample(flac_folder)

def iso_to_flac(iso_file, path):
    output = subprocess.run(['sacd_extract', '-P', '-i', str(iso_file)],
                            capture_output=True, text=True, cwd=str(path)).stdout

    if "Stereo" in output or "2 Channel" in output:
        stereo_path = path.parent / f"{path.name} (Stereo)"
        stereo_path.mkdir(parents=True, exist_ok=True)

        initial_dirs = {d.name for d in stereo_path.iterdir() if d.is_dir()}

        subprocess.run(['sacd_extract', '-2', '-p', '-c', '-i', str(iso_file)], cwd=str(stereo_path))

        new_dirs = [d for d in stereo_path.iterdir() if d.is_dir() and d.name not in initial_dirs]

        if len(new_dirs) != 1:
            log_to_file(f"Expected one new directory in stereo, but found: {len(new_dirs)}. Found multiple directories: {[d.name for d in new_dirs]}")
            return None

        new_dir = new_dirs[0]
        dff_to_flac(new_dir)
        return new_dir

    if "Multichannel" in output or "5 Channel" in output or "6 Channel" in output:
        mch_path = path.parent / f"{path.name} (Multichannel)"
        mch_path.mkdir(parents=True, exist_ok=True)

        initial_dirs = {d.name for d in mch_path.iterdir() if d.is_dir()}

        subprocess.run(['sacd_extract', '-m', '-p', '-c', '-i', str(iso_file)], cwd=str(mch_path))

        new_dirs = [d for d in mch_path.iterdir() if d.is_dir() and d.name not in initial_dirs]

        if len(new_dirs) != 1:
            log_to_file(f"Expected one new directory in multichannel, but found: {len(new_dirs)}. Found multiple directories: {[d.name for d in new_dirs]}")
            return None

        new_dir = new_dirs[0]
        dff_to_flac(new_dir)
        return new_dir

    if not any(keyword in output for keyword in ["Stereo", "2 Channel", "Multichannel", "5 Channel", "6 Channel"]):
        log_to_file(f"Audio for {iso_file} is neither multichannel nor stereo.")
        return None

def check_dynamic_range(directory):
    dr_gains = []

    for file in Path(directory).rglob("*.dff"):
        output = subprocess.run(['ffmpeg', '-i', str(file), '-af', 'volumedetect', '-f', 'null', '-'],
                                capture_output=True, text=True)
        dr_gain = [float(match.group(1)) for match in re.finditer(r'max_volume: (-?\d+(\.\d+)?) dB', output.stderr)]
        dr_gains.extend(dr_gain)

    max_dr_gain = max(dr_gains) if dr_gains else None

    return max_dr_gain

def dff_to_flac(input_folder):
    files = list(input_folder.glob("*.dff"))
    dynamic_range = check_dynamic_range(input_folder)

    if dynamic_range is None:
        log_to_file("No dynamic range found.")
        exit()

    dynamic_range -= 0.5

    for file in files:
        flac_file = file.with_suffix('.flac')

        subprocess.run(
            ['ffmpeg', '-i', str(file), '-vn', '-c:a', 'flac', '-sample_fmt', 's32', '-ar', '88200',
             '-af', f"volume={dynamic_range}", '-dither_method', 'triangular', str(flac_file)])

        trimmed_flac_file = flac_file.with_name(flac_file.stem + ' - Trimmed.flac')

        subprocess.run(
            ['sox', str(flac_file), str(trimmed_flac_file), 'trim', '0.0065', 'reverse', 'silence', '1',
             '0',
             '0%', 'trim', '0.0065', 'reverse', 'pad', '0.0065', '0.2'])

        if trimmed_flac_file.exists():
            flac_file.unlink()
            trimmed_flac_file.rename(flac_file)
        else:
            log_to_file(f"{trimmed_flac_file} not found.")

    check_dff_and_flac(input_folder)

def check_dff_and_flac(input_folder):
    print(f"DFF and FLAC conversion invoked on {input_folder}")

    flac_count = len(list(input_folder.glob("*.flac")))
    dff_files = list(input_folder.glob("*.dff"))
    dff_count = len(dff_files)

    if flac_count == dff_count:
        for dff_file in dff_files:
            dff_file.unlink()
    else:
        log_to_file(f"Unequal number of FLAC and DFF files in {input_folder}.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: script.py <root_dir> <FolderPath>")
        sys.exit(1)

    extract_sacds(Path(sys.argv[1]))