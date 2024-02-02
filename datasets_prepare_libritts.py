# Ignore warnings
import warnings
warnings.filterwarnings("ignore")

import csv
import os
import multiprocessing
import glob
import pandas as pd
import torch
import torchaudio
from pathlib import Path
from tqdm import tqdm
from utils.dataset import load_common_voice_files
from supervoice.audio import load_mono_audio, spectogram
from utils.audio trim_silence
from train_config import config
import torchaudio
import os

#
# Parameters
#

PARAM_WORKERS = 4

#
# Execution
#

def speaker_directory(speaker):
    return str(speaker).zfill(8)

def execute_parallel(args):
    files, index = args
    file, text, speaker = files[index]

    # Format filename from index (e.g. 000001)
    target_name = str(index).zfill(8)

    # Load audio
    waveform = load_mono_audio(file, 16000, device="cuda:1")

    # Trim silence
    waveform = trim_silence(waveform, 16000)

    # Spectogram
    spec = spectogram(waveform, config.audio.n_fft, config.audio.n_mels, config.audio.hop_size, config.audio.win_size, config.audio.sample_rate)

    # Save
    target_dir = os.path.join("datasets", "libritts-prepared", speaker_directory(speaker))
    torchaudio.save(os.path.join(target_dir, target_name + ".wav"), waveform.unsqueeze(0).cpu(), 16000)
    torch.save(spec.cpu(), os.path.join(target_dir, target_name + ".pt"))
    with open(os.path.join(target_dir, target_name + ".txt"), "w", encoding="utf-8") as f:
        f.write(text)
    

def execute_run():

    # Indexing files
    print("Build file index...")
    files = []
    speakers = {}

    # Load vctk corpus
    for file in (glob.glob("external_datasets/libritts-r-clean-100/*/*/*.wav") + glob.glob("external_datasets/libritts-r-360/*/*/*.wav")):
        p = Path(file)
        filename = p.name
        directory = p.parent
        speaker = "libritts_" + p.parents[1].name

         # Load text
        base = filename[:-4]
        text_file = os.path.join(directory, base + ".normalized.txt")
        if os.path.exists(text_file):
            with open(text_file, "r") as f:
                    text = f.read()
        else:
            print("Text not found: " + text_file)
            continue # not found

        # Extract speaker
        if speaker not in speakers:
            speakers[speaker] = len(speakers)
        speaker = speakers[speaker]

        # Append
        files.append((file, text, speaker))
        
    # Results
    print("Files: " + str(len(files)))

    # Creating directories
    for speaker in speakers:
        Path("datasets/libritts-prepared/" + speaker_directory(speakers[speaker])).mkdir(parents=True, exist_ok=True)

    # Indexes loop
    print("Preparing files...")
    with multiprocessing.Manager() as manager:
        files = manager.list(files)
        args_list = [(files, i) for i in range(len(files))]
        with multiprocessing.Pool(processes=PARAM_WORKERS) as pool:
            for result in tqdm(pool.imap_unordered(execute_parallel, args_list, chunksize=32), total=len(files)):
                # if result is not None:
                #     output_test_ok.append(result)
                pass
    
    # # Save results
    print("Saving results...")
    # output_test = pd.DataFrame(output_test_ok)
    # output_test.to_pickle("./datasets/cv_validated_test.pkl")
    # output_train = pd.DataFrame(output_train_ok)
    # output_train.to_pickle("./datasets/cv_validated_train.pkl")

if __name__ == "__main__":
    execute_run()