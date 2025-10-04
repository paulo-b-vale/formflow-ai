#!/usr/bin/env python3
"""
Script to convert OGG audio files to WAV format.
This script is designed to work within the Docker container environment.
"""

import os
import sys
from pydub import AudioSegment

def convert_ogg_to_wav(input_file_path, output_file_path=None):
    """
    Convert an OGG audio file to WAV format.
    
    :param input_file_path: Path to the input OGG file
    :param output_file_path: Path for the output WAV file (optional)
    :return: Path to the converted WAV file
    """
    # Validate input file exists
    if not os.path.exists(input_file_path):
        raise FileNotFoundError(f"Input file {input_file_path} not found")
    
    # If no output file path is provided, generate one
    if output_file_path is None:
        base_name = os.path.splitext(input_file_path)[0]
        output_file_path = f"{base_name}.wav"
    
    try:
        # Load the OGG file
        audio = AudioSegment.from_ogg(input_file_path)
        
        # Export as WAV
        audio.export(output_file_path, format="wav")
        
        print(f"Successfully converted {input_file_path} to {output_file_path}")
        return output_file_path
    except Exception as e:
        print(f"Error converting file: {str(e)}")
        raise

def convert_all_ogg_in_directory(directory_path):
    """
    Convert all OGG files in a directory to WAV format.
    
    :param directory_path: Path to the directory containing OGG files
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Directory {directory_path} not found")
    
    converted_files = []
    for filename in os.listdir(directory_path):
        if filename.endswith(".ogg"):
            input_file_path = os.path.join(directory_path, filename)
            try:
                output_file_path = convert_ogg_to_wav(input_file_path)
                converted_files.append(output_file_path)
            except Exception as e:
                print(f"Failed to convert {filename}: {str(e)}")
    
    return converted_files

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_ogg_to_wav.py <input_file_or_directory>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    if os.path.isfile(input_path) and input_path.endswith(".ogg"):
        try:
            convert_ogg_to_wav(input_path)
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)
    elif os.path.isdir(input_path):
        try:
            converted_files = convert_all_ogg_in_directory(input_path)
            print(f"Converted {len(converted_files)} files")
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)
    else:
        print("Please provide a valid OGG file or directory containing OGG files.")
        sys.exit(1)