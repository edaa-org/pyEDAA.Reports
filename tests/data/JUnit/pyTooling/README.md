# Extract GitHub Artifacts

```posh
foreach ($directory in (dir)) {
	$name = $directory.BaseName
	Expand-Archive "$name.zip"
	mv $name\*.xml "$name.xml"
	rm $name
}
```
