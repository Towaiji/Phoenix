import subprocess
import sys
from pathlib import Path

EXAMPLES_DIR = Path("examples")

EXPECTED_FAIL = {
    "bad_type.py",
    "bad_list.py",
    "bad_eval.py",
    "bad_exec.py",
    "bad_import.py",
    "bad_import_alias.py",
    "bad_import_from_module.py",
    "bad_while.py",
    "bad_while_uninitialized.py",
    "bad_while_double_update.py",
    "bad_while_wrong_direction.py",
    "bad_while_other_mutation.py",
    "bad_for_dynamic.py",
    "bad_for_range_nonliteral.py",
    "bad_for_iter_unknown_list.py",
    "bad_for_range_zero_step.py",
    "bad_len_unknown_list.py",
    "bad_list_append_type.py",
    "bad_list_pop_args.py",
    "bad_list_slice_step.py",
    "bad_list_slice_static.py",
    "bad_dict_key_type.py",
    "bad_dict_empty.py",
    "bad_dict_literal_lookup.py",
    "bad_dict_mixed_keys.py",
    "bad_dict_mixed_values.py",
    "bad_dict_update_key_type.py",
    "bad_dict_update_value_type.py",
    "bad_set_mixed_types.py",
    "bad_set_in_wrong_type.py",
    "bad_set_add_type.py",
    "bad_set_remove_type.py",
    "bad_str_list.py",
    "bad_minmax_empty.py",
    "bad_minmax_list_non_numeric.py",
    "bad_string_method_args.py",
    "bad_string_method_receiver.py",
    "bad_index_oob.py",
    "bad_index_negative.py",
    "bad_index_non_int.py",
    "bad_if_missing_else.py",
    "bad_if_partial_assign.py",
    "bad_if_type.py",
    "bad_if_condition.py",
    "bad_string_mixed.py",
    "bad_big.py",
    "bad_logical_operands.py",
    "bench_python.py"
}

def run_test(file_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "phoenix.cli",
            str(file_path),
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr

def main():
    passed = 0
    failed = 0

    for file in sorted(EXAMPLES_DIR.glob("*.py")):
        code, output = run_test(file)
        name = file.name

        if name in EXPECTED_FAIL:
            if code != 0:
                print(f"✓ {name} correctly rejected")
                passed += 1
            else:
                print(f"✗ {name} SHOULD have failed but passed")
                print(output)
                failed += 1
        else:
            if code == 0:
                print(f"✓ {name} correctly accepted")
                passed += 1
            else:
                print(f"✗ {name} SHOULD have passed but failed")
                print(output)
                failed += 1

    print("\nSummary:")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
