import os
import yaml

def rebuild_documents_txt(playbooks_dir, output_file):
    """
    Rebuilds the documents.txt file by processing YAML playbooks
    in the specified directory.

    Args:
        playbooks_dir (str): Directory containing the playbook files.
        output_file (str): Path to the output documents.txt file.
    """
    print(f"Rebuilding {output_file} from playbooks in {playbooks_dir}...")

    # Ensure the playbooks directory exists
    if not os.path.exists(playbooks_dir):
        print(f"Error: Playbooks directory {playbooks_dir} does not exist.")
        return

    # Open the output file for writing
    with open(output_file, "w") as out_file:
        for filename in os.listdir(playbooks_dir):
            filepath = os.path.join(playbooks_dir, filename)

            # Skip non-YAML files
            if not filename.endswith(".yml") and not filename.endswith(".yaml"):
                print(f"Skipping non-YAML file: {filename}")
                continue

            print(f"Processing playbook: {filename}")

            # Load and validate the YAML file
            try:
                with open(filepath, "r") as playbook_file:
                    playbook = yaml.safe_load(playbook_file)

                # Ensure the playbook contains tasks or a valid structure
                if not isinstance(playbook, list) or not any("tasks" in item for item in playbook):
                    print(f"Skipping invalid playbook structure: {filename}")
                    continue

                # Extract and flatten tasks
                for section in playbook:
                    if "tasks" in section:
                        for task in section["tasks"]:
                            out_file.write(yaml.dump(task, default_flow_style=False))
                            out_file.write("\n---\n")  # Separate tasks with YAML document markers

            except yaml.YAMLError as e:
                print(f"Error processing YAML in file {filename}: {e}")
            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    print(f"Rebuild complete. Flattened playbooks saved to {output_file}.")


playbooks_dir = "existing_playbooks"
output_file = "documents.txt"

rebuild_documents_txt(playbooks_dir, output_file)