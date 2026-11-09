import json
import os

file_path = "symbolic_api.json"
ui_file_path = "../omarg-ui/src/lib/symbolic_api.json"

for path in [file_path, ui_file_path]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Insert meta at the top by creating a new dict
        new_data = {
            "meta": {
                "mapping_principle": "The keyword→Sephira associations are convention-based, not ontological. This is ONE possible symbolic reading.",
                "alternatives_example": {
                    "anger": {
                        "Kabbalistic": "Geburah",
                        "Zen": "Attachment to self",
                        "CBT": "Cognitive distortion",
                        "Neuroscience": "Amygdala activation"
                    }
                },
                "invitation": "This map is offered as a lens. Rewrite it to fit your tradition."
            }
        }
        
        new_data.update(data)
        
        # Overwrite metadata version/generated_by
        new_data["metadata"]["version"] = "1.1.0"
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=4)
