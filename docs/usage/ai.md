# Using AI assistants

The repository includes a skill that teaches AI coding assistants how to use
warpx-geometry: the shapes, the WarpX conventions, the RZ rules and common mistakes.
It is a single Markdown file,
[`skills/warpx-geometry/SKILL.md`](https://github.com/BLAST-WarpX/warpx-geometry/blob/main/skills/warpx-geometry/SKILL.md).

## Claude Code

Copy the skill into your personal skills folder, so it is available in every project:

```bash
mkdir -p ~/.claude/skills/warpx-geometry
curl -L -o ~/.claude/skills/warpx-geometry/SKILL.md \
  https://raw.githubusercontent.com/BLAST-WarpX/warpx-geometry/main/skills/warpx-geometry/SKILL.md
```

To share it with everyone working on a project, put it in the project's
`.claude/skills/warpx-geometry/` folder instead. Claude Code loads the skill when a
request matches, and you can also start it with `/warpx-geometry`.

## Other assistants

Many other assistants read the same format. If yours does not, point it to the file,
or paste its contents into the instructions for your project.

## Example requests

- "Build an RZ geometry with three rings at 1, 2 and 3 kV inside a grounded tube."
- "Turn this drawing of an electrode into warpx-geometry, and plot it so I can check
  it."
- "Set up a WarpX inputs file for this geometry with the potential on each electrode."

Always check the result with `plot_2d` or `plot_3d`, since the plots show the
expression that WarpX gets.

## Working on warpx-geometry

The skill is for using the package. For changes to the package itself, assistants
should read
[`AGENTS.md`](https://github.com/BLAST-WarpX/warpx-geometry/blob/main/AGENTS.md).
