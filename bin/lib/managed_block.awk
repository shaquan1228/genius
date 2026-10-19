# Validate the entire input before the caller commits this output.
$0 == "# BEGIN GENIUS" {
    if (inside) { invalid = 1; exit 1 }
    inside = 1
    if (action == "install" && !written) {
        print ENVIRON["GENIUS_IDENTITY_BLOCK"]
        written = 1
    }
    next
}
$0 == "# END GENIUS" {
    if (!inside) { invalid = 1; exit 1 }
    inside = 0
    next
}
!inside { print }
END {
    if (invalid || inside) exit 1
    if (action == "install" && !written) {
        if (NR) print ""
        print ENVIRON["GENIUS_IDENTITY_BLOCK"]
    }
}
