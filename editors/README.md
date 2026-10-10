# Editor support

`tb.tmbundle/` is a TextMate bundle for tb syntax highlighting:

```text
tb.tmbundle/
|-- Syntaxes/
|   `-- tb.tmLanguage.json
`-- info.plist
```

The shared grammar is [tb.tmLanguage.json](tb.tmbundle/Syntaxes/tb.tmLanguage.json).
Its scope is `source.tb`, and its file extension is `.tb`.

## IntelliJ

Enable the TextMate Bundles plugin, then add the `editors/tb.tmbundle` directory
under **Settings > Editor > TextMate Bundles**. Select the bundle directory,
rather than the grammar file or the enclosing `editors` directory.

See the [IntelliJ TextMate documentation](https://www.jetbrains.com/help/idea/textmate.html).

## Other editor plugins

Copy or vendor the grammar from `tb.tmbundle/Syntaxes/tb.tmLanguage.json` into
the plugin's resources and register `source.tb` for `.tb` files. Keep this file
as the source of truth when updating the plugin.

The grammar covers keywords, types, function names, common builtin calls,
operators, comments, and multiline single-quoted strings with tb escapes.
It supports both brace and indentation syntax. Highlighting is lexical:
uppercase constants and type names follow naming conventions, and builtin names
are recognized by spelling even when shadowed by user functions. Semantic
reference resolution belongs in the editor plugin.

Update the grammar alongside `docs/tb.md` when the language changes.
