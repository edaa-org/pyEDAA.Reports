// Package version formats a version number. It has no tests.
package version

import "fmt"

// String formats a version number as major.minor.patch, or major.minor if patch is zero.
func String(major, minor, patch int) string {
	if patch == 0 {
		return fmt.Sprintf("%d.%d", major, minor)
	}
	return fmt.Sprintf("%d.%d.%d", major, minor, patch)
}
