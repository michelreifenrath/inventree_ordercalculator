import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from src.inventree_order_calculator.presets_manager import (
    load_presets_from_file,
    save_presets_to_file,
    add_or_update_preset,
    delete_preset_by_name,
    get_preset_names,
    get_preset_by_name,
)
from src.inventree_order_calculator.presets_manager import (
    PresetItem,
    Preset,
    PresetsFile,
)

# TDD Anchor: Test loading from a non-existent file
def test_load_presets_from_non_existent_file(tmp_path):
    """
    Test that loading from a non-existent file returns a default PresetsFile.
    """
    non_existent_file = tmp_path / "non_existent_presets.json"
    presets_file = load_presets_from_file(non_existent_file)
    assert presets_file == PresetsFile(presets=[], filepath=non_existent_file) # Expect filepath to be set
    assert presets_file.filepath == non_existent_file

# TDD Anchor: Test loading from a malformed JSON file
def test_load_presets_from_malformed_json_file(tmp_path, caplog):
    """
    Test that loading from a malformed JSON file handles JSONDecodeError,
    logs an error, and returns a default PresetsFile.
    """
    malformed_file = tmp_path / "malformed_presets.json"
    malformed_file.write_text("this is not json")

    presets_file = load_presets_from_file(malformed_file)
    assert presets_file == PresetsFile(presets=[], filepath=malformed_file) # Expect filepath to be set
    assert presets_file.filepath == malformed_file
    # The actual log message from presets_manager.py is "JSON decode error loading presets from..."
    assert "JSON decode error loading presets from" in caplog.text
    assert str(malformed_file) in caplog.text

# TDD Anchor: Test loading a valid presets.json file
def test_load_presets_from_valid_file(tmp_path):
    """
    Test loading a valid presets.json file and verify correct parsing.
    """
    valid_file = tmp_path / "valid_presets.json"
    preset_item_data = {"part_id": "R10k", "quantity": 100}
    preset_data = {"name": "Test Preset 1", "items": [preset_item_data]}
    presets_file_data = {"presets": [preset_data]}
    valid_file.write_text(json.dumps(presets_file_data))

    expected_preset_item = PresetItem(part_id="R10k", quantity=100)
    expected_preset = Preset(name="Test Preset 1", items=[expected_preset_item])
    expected_presets_file = PresetsFile(presets=[expected_preset], filepath=valid_file)

    loaded_presets_file = load_presets_from_file(valid_file)
    assert loaded_presets_file == expected_presets_file
    assert loaded_presets_file.filepath == valid_file
    assert len(loaded_presets_file.presets) == 1
    assert loaded_presets_file.presets[0].name == "Test Preset 1"
    assert len(loaded_presets_file.presets[0].items) == 1
    assert loaded_presets_file.presets[0].items[0].part_id == "R10k"


# TDD Anchor: Test saving PresetsFile data
def test_save_presets_to_file(tmp_path):
    """
    Test saving PresetsFile data and verify the content of the written JSON file.
    """
    output_file = tmp_path / "output_presets.json"
    preset_item1 = PresetItem(part_id="C10uF", quantity=50)
    preset1 = Preset(name="Caps", items=[preset_item1])
    preset_item2 = PresetItem(part_id="LED_R", quantity=200)
    preset2 = Preset(name="LEDs", items=[preset_item2])
    presets_to_save = PresetsFile(presets=[preset1, preset2], filepath=output_file)

    save_presets_to_file(presets_to_save, filepath=output_file) # Pass the output_file path

    assert output_file.exists()
    saved_data = json.loads(output_file.read_text())
    
    # The model_dump_json will not include the 'filepath' field by default unless include is specified.
    # Also, PresetItem and Preset do not have a 'metadata' field.
    expected_data = {
        "presets": [
            {"name": "Caps", "items": [{"part_id": "C10uF", "quantity": 50}]},
            {"name": "LEDs", "items": [{"part_id": "LED_R", "quantity": 200}]}
        ]
        # filepath is not part of the JSON dump for the root model by default
    }
    assert len(saved_data["presets"]) == len(expected_data["presets"])
    
    # Check content more carefully
    assert saved_data["presets"][0]["name"] == "Caps"
    assert saved_data["presets"][0]["items"][0]["part_id"] == "C10uF"
    assert saved_data["presets"][0]["items"][0]["quantity"] == 50
    assert saved_data["presets"][1]["name"] == "LEDs"
    assert saved_data["presets"][1]["items"][0]["part_id"] == "LED_R"
    assert saved_data["presets"][1]["items"][0]["quantity"] == 200


# TDD Anchor: Test I/O error during write
@patch("pathlib.Path.write_text")
def test_save_presets_to_file_io_error(mock_write_text, tmp_path, caplog):
    """
    Test that an I/O error during file write is caught, logged, and an exception is raised.
    """
    output_file = tmp_path / "error_presets.json"
    presets_to_save = PresetsFile(presets=[], filepath=output_file)
    
    mock_write_text.side_effect = IOError("Disk full")

    with pytest.raises(IOError) as excinfo:
        save_presets_to_file(presets_to_save, filepath=output_file) # Pass the output_file path
    
    assert "Disk full" in str(excinfo.value)
    # The log message in save_presets_to_file uses the filepath passed to it.
    assert f"IOError saving presets to {output_file}" in caplog.text
    assert "Disk full" in caplog.text


# TDD Anchor: Test adding a new preset to an empty PresetsFile
def test_add_new_preset_to_empty_presets_file(tmp_path):
    """
    Test adding a new preset to an empty PresetsFile.
    """
    presets_file = PresetsFile(presets=[], filepath=tmp_path / "presets.json")
    new_preset = Preset(name="New Preset", items=[PresetItem(part_id="PA001", quantity=10)])

    updated_presets_file = add_or_update_preset(presets_file, new_preset)

    assert len(updated_presets_file.presets) == 1
    assert updated_presets_file.presets[0] == new_preset
    assert updated_presets_file.filepath == presets_file.filepath

# TDD Anchor: Test adding a new preset to an existing PresetsFile
def test_add_new_preset_to_existing_presets_file(tmp_path):
    """
    Test adding a new preset to an existing PresetsFile.
    """
    existing_preset = Preset(name="Existing Preset", items=[PresetItem(part_id="PB002", quantity=20)])
    presets_file = PresetsFile(presets=[existing_preset], filepath=tmp_path / "presets.json")
    new_preset = Preset(name="New Preset", items=[PresetItem(part_id="PA001", quantity=10)])

    updated_presets_file = add_or_update_preset(presets_file, new_preset)

    assert len(updated_presets_file.presets) == 2
    assert existing_preset in updated_presets_file.presets
    assert new_preset in updated_presets_file.presets

# TDD Anchor: Test updating an existing preset by name
def test_update_existing_preset(tmp_path):
    """
    Test updating an existing preset by name.
    """
    preset_item1 = PresetItem(part_id="PC003", quantity=30)
    preset1_v1 = Preset(name="My Preset", items=[preset_item1])
    
    preset_item2 = PresetItem(part_id="PD004", quantity=5)
    preset2 = Preset(name="Another Preset", items=[preset_item2])
    
    presets_file = PresetsFile(presets=[preset1_v1, preset2], filepath=tmp_path / "presets.json")

    preset1_v2_items = [PresetItem(part_id="PC003_U", quantity=35), PresetItem(part_id="PE005", quantity=15)]
    preset1_v2 = Preset(name="My Preset", items=preset1_v2_items)

    updated_presets_file = add_or_update_preset(presets_file, preset1_v2)

    assert len(updated_presets_file.presets) == 2
    
    # Check that the updated preset is present
    found_updated = False
    for p in updated_presets_file.presets:
        if p.name == "My Preset":
            assert p.items == preset1_v2_items
            found_updated = True
            break
    assert found_updated, "Updated preset 'My Preset' not found or items mismatch."

    # Check that the other preset is untouched
    found_other = False
    for p in updated_presets_file.presets:
        if p.name == "Another Preset":
            assert p.items == [preset_item2] # Original items
            found_other = True
            break
    assert found_other, "Preset 'Another Preset' was modified or removed."


# TDD Anchor: Test deleting an existing preset
def test_delete_existing_preset(tmp_path):
    """
    Test deleting an existing preset by name.
    """
    preset1 = Preset(name="PresetToDelete", items=[PresetItem(part_id="PX001", quantity=1)])
    preset2 = Preset(name="PresetToKeep", items=[PresetItem(part_id="PY002", quantity=2)])
    presets_file = PresetsFile(presets=[preset1, preset2], filepath=tmp_path / "presets.json")

    updated_presets_file = delete_preset_by_name(presets_file, "PresetToDelete")

    assert len(updated_presets_file.presets) == 1
    assert updated_presets_file.presets[0].name == "PresetToKeep"
    assert updated_presets_file.filepath == presets_file.filepath
    
    # Verify original object is not modified if deepcopy is not used internally by the function
    # This depends on the implementation of delete_preset_by_name
    # For now, we assume it returns a new or modified PresetsFile object
    assert len(presets_file.presets) == 2


# TDD Anchor: Test attempting to delete a non-existent preset
def test_delete_non_existent_preset(tmp_path):
    """
    Test attempting to delete a non-existent preset.
    The list should remain unchanged and no error should occur.
    """
    preset1 = Preset(name="ExistingPreset1", items=[PresetItem(part_id="PA001", quantity=10)])
    preset2 = Preset(name="ExistingPreset2", items=[PresetItem(part_id="PB002", quantity=20)])
    presets_file = PresetsFile(presets=[preset1, preset2], filepath=tmp_path / "presets.json")

    updated_presets_file = delete_preset_by_name(presets_file, "NonExistentPreset")

    assert len(updated_presets_file.presets) == 2
    assert presets_file.presets == updated_presets_file.presets # Expect no change
    assert updated_presets_file.filepath == presets_file.filepath


# TDD Anchor: Test get_preset_names with empty PresetsFile
def test_get_preset_names_empty(tmp_path):
    """
    Test get_preset_names with an empty PresetsFile.
    """
    presets_file = PresetsFile(presets=[], filepath=tmp_path / "presets.json")
    names = get_preset_names(presets_file)
    assert names == []

# TDD Anchor: Test get_preset_names with multiple presets
def test_get_preset_names_multiple_presets(tmp_path):
    """
    Test get_preset_names with multiple presets, verifying correct names and order.
    """
    preset1 = Preset(name="Alpha Preset", items=[])
    preset2 = Preset(name="Beta Preset", items=[])
    preset3 = Preset(name="Gamma Preset", items=[])
    # Intentionally adding in a different order to test if sorting/ordering is handled if required
    # For now, assuming the order of the list is preserved.
    presets_file = PresetsFile(presets=[preset2, preset1, preset3], filepath=tmp_path / "presets.json")
    
    names = get_preset_names(presets_file)
    assert names == ["Beta Preset", "Alpha Preset", "Gamma Preset"]


# TDD Anchor: Test getting an existing preset
def test_get_preset_by_name_existing(tmp_path):
    """
    Test getting an existing preset by its name.
    """
    preset_item = PresetItem(part_id="TP001", quantity=10)
    preset_to_find = Preset(name="MyTargetPreset", items=[preset_item])
    other_preset = Preset(name="AnotherPreset", items=[])
    presets_file = PresetsFile(
        presets=[other_preset, preset_to_find],  # Order shouldn't matter
        filepath=tmp_path / "presets.json"
    )

    found_preset = get_preset_by_name(presets_file, "MyTargetPreset")
    assert found_preset is not None
    assert found_preset == preset_to_find
    assert found_preset.name == "MyTargetPreset"
    assert found_preset.items[0].part_id == "TP001"

# TDD Anchor: Test getting a non-existent preset
def test_get_preset_by_name_non_existent(tmp_path):
    """
    Test getting a non-existent preset by its name. Should return None.
    """
    preset1 = Preset(name="ExistingPreset1", items=[])
    presets_file = PresetsFile(presets=[preset1], filepath=tmp_path / "presets.json")

    found_preset = get_preset_by_name(presets_file, "NonExistentPresetName")
    assert found_preset is None