function uploadFile() {
    let fileInput = document.getElementById("fileInput");
    let fileInfo = document.getElementById("fileInfo");

    if (fileInput.files.length === 0) {
        alert("Please select a file first.");
        return;
    }

    let fileName = fileInput.files[0].name;
    fileInfo.innerHTML = "File Uploaded: " + fileName;

    alert("File uploaded successfully! (Backend will process it in the next step)");
}
