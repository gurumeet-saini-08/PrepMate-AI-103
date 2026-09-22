// PrepMate Performance Report JS
document.addEventListener("DOMContentLoaded", () => {
  // Print Report Handler
  const printBtn = document.getElementById("printReportBtn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      window.print();
    });
  }

  // Accordion Expand/Collapse for Questions
  const questionHeaders = document.querySelectorAll(".question-item-header");
  questionHeaders.forEach((header) => {
    header.addEventListener("click", () => {
      const body = header.nextElementSibling;
      if (body) {
        body.style.display = body.style.display === "none" ? "block" : "none";
      }
    });
  });
});
