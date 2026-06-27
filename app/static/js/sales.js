(function () {
  const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

  async function apiPost(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  }

  function reloadPage() {
    window.location.reload();
  }

  document.querySelectorAll(".add-product-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await apiPost("/sales/cart/add", {
          product_id: parseInt(btn.dataset.id, 10),
          quantity: 1,
        });
        reloadPage();
      } catch (e) {
        alert(e.message);
      }
    });
  });

  document.getElementById("clearCartBtn")?.addEventListener("click", async () => {
    await apiPost("/sales/cart/clear", {});
    reloadPage();
  });

  document.querySelectorAll(".remove-item").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const row = btn.closest("tr");
      const productId = parseInt(row.dataset.productId, 10);
      await apiPost("/sales/cart/remove", { product_id: productId });
      reloadPage();
    });
  });

  document.querySelectorAll(".cart-qty").forEach((input) => {
    input.addEventListener("change", async () => {
      const row = input.closest("tr");
      const productId = parseInt(row.dataset.productId, 10);
      try {
        await apiPost("/sales/cart/update", {
          product_id: productId,
          quantity: parseInt(input.value, 10),
        });
        reloadPage();
      } catch (e) {
        alert(e.message);
        reloadPage();
      }
    });
  });

  const searchInput = document.getElementById("productSearch");
  const searchResults = document.getElementById("searchResults");
  let searchTimeout;

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(searchTimeout);
      const q = searchInput.value.trim();
      if (q.length < 1) {
        searchResults.innerHTML = "";
        return;
      }
      searchTimeout = setTimeout(async () => {
        const res = await fetch(`/sales/search?q=${encodeURIComponent(q)}`);
        const products = await res.json();
        searchResults.innerHTML = products
          .map(
            (p) =>
              `<button type="button" class="list-group-item list-group-item-action search-add" data-id="${p.id}">
                <div class="d-flex justify-content-between">
                  <span>${p.name} <small class="text-muted">${p.barcode || ""}</small></span>
                  <span>KSh ${p.price.toLocaleString()} · ${p.stock} in stock</span>
                </div>
              </button>`
          )
          .join("");

        searchResults.querySelectorAll(".search-add").forEach((el) => {
          el.addEventListener("click", async () => {
            try {
              await apiPost("/sales/cart/add", {
                product_id: parseInt(el.dataset.id, 10),
                quantity: 1,
              });
              searchInput.value = "";
              searchResults.innerHTML = "";
              reloadPage();
            } catch (e) {
              alert(e.message);
            }
          });
        });
      }, 250);
    });

    searchInput.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const first = searchResults.querySelector(".search-add");
        if (first) first.click();
      }
    });
  }

  document.getElementById("clearSearch")?.addEventListener("click", () => {
    searchInput.value = "";
    searchResults.innerHTML = "";
  });

  const paymentMethod = document.getElementById("paymentMethod");
  const mpesaPhoneGroup = document.getElementById("mpesaPhoneGroup");
  if (paymentMethod && mpesaPhoneGroup) {
    const toggleMpesa = () => {
      mpesaPhoneGroup.style.display = paymentMethod.value === "mpesa" ? "block" : "none";
    };
    paymentMethod.addEventListener("change", toggleMpesa);
    toggleMpesa();
  }
})();
