function pollMpesaPayment(paymentId, options) {
  const statusBox = document.getElementById("statusBox");
  const backLink = document.getElementById("backLink");
  let attempts = 0;
  const maxAttempts = 60;

  async function poll() {
    attempts += 1;
    try {
      const res = await fetch(`/api/mpesa/status/${paymentId}`);
      const data = await res.json();

      if (data.status === "completed") {
        statusBox.className = "alert alert-success";
        if (options.paymentType === "sale" && data.sale_id) {
          statusBox.textContent = "Payment confirmed! Opening receipt...";
          window.location.href = options.successUrl.replace(/\/\d+$/, "/" + data.sale_id);
        } else {
          statusBox.textContent = "Payment confirmed! Subscription activated.";
          setTimeout(() => (window.location.href = options.successUrl), 1500);
        }
        return;
      }

      if (data.status === "failed" || data.status === "cancelled") {
        statusBox.className = "alert alert-danger";
        statusBox.textContent = data.result_desc || "Payment failed or was cancelled.";
        backLink.style.display = "inline";
        return;
      }

      if (attempts >= maxAttempts) {
        statusBox.className = "alert alert-warning";
        statusBox.textContent = "Still waiting. Check your phone or try again.";
        backLink.style.display = "inline";
        return;
      }

      setTimeout(poll, 3000);
    } catch (e) {
      if (attempts < maxAttempts) {
        setTimeout(poll, 3000);
      }
    }
  }

  poll();
}
