function viewData() {
    fetch("/view_academic_info")
    .then(response => {
        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }
        return response.json();
    })
    .then(data => {
        let output = "<h3>Saved Data</h3><ul class='list-group'>";
        if (data.length === 0) {
            output += "<li class='list-group-item text-danger'>No records found.</li>";
        } else {
            data.forEach(item => {
                output += `<li class="list-group-item">
                    <strong>Department:</strong> ${item.department} |
                    <strong>Year:</strong> ${item.academic_year} |
                    <strong>Semester:</strong> ${item.semester}
                </li>`;
            });
        }
        output += "</ul>";
        document.getElementById("view-results").innerHTML = output;
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Failed to fetch data. Check console for details.");
    });
}
