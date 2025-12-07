# src/env.py
"""
Environment for Chain-of-Edits (CoE) as described in the paper.
Implements:
- ScratchpadState: holds code lines + feedback
- DSLExecutor: runs code and tests via exec()
- CoEEnv: applies DSL actions to code and updates execution feedback

Safe for local reproduction. DO NOT run untrusted code.
"""

import re
import traceback
from copy import deepcopy


# ============================
# Scratchpad State
# ============================

class ScratchpadState:
    def __init__(self, code_lines, feedback=""):
        # store a COPY of user code lines
        self.code_lines = list(code_lines)
        self.feedback = feedback

    def render(self):
        """
        Render code with line numbers + feedback, exactly like the paper.
        Format:
        L 1 <line1>
        L 2 <line2>
        ...
        ***
        <feedback>
        """
        numbered = [f"L {i+1} {self.code_lines[i]}" for i in range(len(self.code_lines))]
        return "\n".join(numbered) + "\n***\n" + (self.feedback or "")


# ============================
# Execute code + tests
# ============================

class DSLExecutor:
    def __init__(self, tests):
        """
        tests: list of test strings (from MBPP)
        Each test is executed using exec().
        """
        self.tests = tests

    def run(self, code_text):
        """
        Execute candidate solution code + tests.
        Returns "" if all tests pass, else returns traceback + test failure summary.
        """
        try:
            g = {}  # execution namespace
            exec(code_text, g, g)

            failed = []
            for idx, test in enumerate(self.tests, 1):
                try:
                    exec(test, g, g)
                except Exception as e:
                    failed.append((idx, test, repr(e)))

            if not failed:
                return ""  # PASSED all tests

            # create detailed failure message
            return "\n".join([
                f"Test {i} failed!\nTest code:\n{t}\nError: {err}"
                for (i, t, err) in failed
            ])

        except Exception:
            # SyntaxError, NameError, etc.
            return traceback.format_exc()


# ============================
# CoE Environment
# ============================

class CoEEnv:
    """
    - Holds scratchpad state (code + feedback)
    - Applies DSL actions:
        DELL <line>
        ADDL <line> >>><code>
        REPL <line> >>><code>
        REPW <line> >>><old> >>><new>
        EXIT
    - After every action, feedback is recomputed by running code + tests.
    """
    def __init__(self, code_lines, tests):
        self.state = ScratchpadState(code_lines, "")
        self.exec = DSLExecutor(tests)
        self.update_feedback()

    # ------------------------
    # Re-run code & tests
    # ------------------------
    def update_feedback(self):
        code_text = "\n".join(self.state.code_lines)
        self.state.feedback = self.exec.run(code_text)

    # ------------------------
    # Apply a DSL action
    # ------------------------
    def apply(self, action):
        action = action.strip()
        parts = action.split()

        # ----------- DELETE LINE -----------
        if parts[0] == "DELL":
            if len(parts) >= 2 and parts[1].isdigit():
                ln = int(parts[1])
                if 1 <= ln <= len(self.state.code_lines):
                    self.state.code_lines.pop(ln - 1)

         # ----------- ADD LINE -----------
        elif parts[0] == "ADDL":
            # Format: ADDL <line> >>><content>
            if len(parts) >= 2 and parts[1].isdigit():
                ln = int(parts[1])
                if ">>>" in action:
                    insertion = action.split(">>>", 1)[1]
                else:
                    insertion = ""

                # Clamp ln to valid range: 1 → len(code_lines)+1
                ln = max(1, min(ln, len(self.state.code_lines) + 1))

                self.state.code_lines.insert(ln - 1, insertion)


        # ----------- REPLACE LINE -----------
        elif parts[0] == "REPL":
            # Format: REPL <line> >>><content>
            if len(parts) >= 2 and parts[1].isdigit():
                ln = int(parts[1])
                if ">>>" in action:
                    replacement = action.split(">>>", 1)[1]
                else:
                    replacement = ""

                # Only replace if the line exists
                if 1 <= ln <= len(self.state.code_lines):
                    self.state.code_lines[ln - 1] = replacement
                else:
                    # If invalid → ignore gracefully
                    pass

        # ----------- REPLACE WORD -----------
        elif parts[0] == "REPW":
            # Format: REPW <line> >>>old>>>new
            # Example: REPW 3 >>>return>>>yield
            m = re.match(r"REPW\s+(\d+)\s+>>>(.*?)>>>(.*)$", action)
            if m:
                ln = int(m.group(1))
                old = m.group(2)
                new = m.group(3)
                if 1 <= ln <= len(self.state.code_lines):
                    self.state.code_lines[ln - 1] = self.state.code_lines[ln - 1].replace(old, new)

        # ----------- EXIT -----------
        elif parts[0] == "EXIT":
            # Nothing to modify, but allowed.
            pass

        # After modification → recompute execution feedback
        self.update_feedback()

        # Return a *deep copy* so model never accidentally mutates internal state
        return deepcopy(self.state)
