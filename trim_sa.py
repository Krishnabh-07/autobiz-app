lines = open(r"frontend/superadmin.html", encoding="utf-8").readlines()
keep = lines[:859]
keep.append("</body>\n")
keep.append("</html>\n")
open(r"frontend/superadmin.html", "w", encoding="utf-8").writelines(keep)
print("Done. Lines:", len(keep))
