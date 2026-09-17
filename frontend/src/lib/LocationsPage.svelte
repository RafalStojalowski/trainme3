<script>
  import { onMount, onDestroy } from "svelte";
  import { fade, fly, slide } from "svelte/transition";
  import { cubicInOut } from "svelte/easing";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";

  const LAYOUT_TRANSITION_MS = 500;

  let { onBack } = $props();

  const POLAND_CENTER = [52.05, 19.48];
  const POLAND_ZOOM = 6;

  let mapContainer;
  let map;
  let markers = [];
  let locationPickerMarker;
  let pickerActive = false;

  let locations = $state([]);
  let loading = $state(true);
  let searchQuery = $state("");

  let detailLocation = $state(null);
  let detailLoading = $state(false);

  let showAddRoomForm = $state(false);
  let newRoomName = $state("");
  let newRoomCapacity = $state(2);
  let newRoomPrice = $state(200);
  let newRoomAmenities = $state("");
  let addingRoom = $state(false);
  let addRoomError = $state("");

  let editingRoomId = $state(null);
  let editRoomName = $state("");
  let editRoomCapacity = $state(2);
  let editRoomPrice = $state(200);
  let editRoomAmenities = $state("");
  let savingRoom = $state(false);
  let editRoomError = $state("");

  let confirmDeleteRoomId = $state(null);
  let deletingRoom = $state(false);

  let showAddLocationPanel = $state(false);
  let newLocationName = $state("");
  let newLocationAddress = $state("");
  let newLocationDescription = $state("");
  let newLocationLat = $state(52.2297);
  let newLocationLng = $state(21.0122);
  let addingLocation = $state(false);
  let addLocationError = $state("");

  let editingLocationId = $state(null);
  let editLocationName = $state("");
  let editLocationAddress = $state("");
  let editLocationDescription = $state("");
  let editLocationLat = $state(52.2297);
  let editLocationLng = $state(21.0122);
  let savingLocationDetails = $state(false);
  let editLocationError = $state("");

  let filteredLocations = $derived(
    locations.filter((location) => {
      const query = searchQuery.trim().toLowerCase();
      if (!query) return true;
      return (
        location.name.toLowerCase().includes(query) ||
        location.address.toLowerCase().includes(query)
      );
    }),
  );

  let currentReservations = $derived(
    detailLocation?.rooms.filter((room) => room.current_reservation) ?? [],
  );

  const pinIcon = L.divIcon({
    className: "location-pin",
    html: '<div class="pin-body"><i class="fa-solid fa-building"></i></div>',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -30],
  });

  function renderMarkers() {
    markers.forEach((marker) => marker.remove());
    markers = locations.map((location) =>
      L.marker([location.latitude, location.longitude], { icon: pinIcon })
        .addTo(map)
        .bindPopup(`<strong>${location.name}</strong><br>${location.address}`),
    );
  }

  async function loadLocations() {
    loading = true;
    try {
      const res = await fetch("/api/locations", { credentials: "include" });
      if (res.ok) {
        locations = await res.json();
        renderMarkers();
      }
    } finally {
      loading = false;
    }
  }

  function focusLocation(location) {
    map?.flyTo([location.latitude, location.longitude], 14, { duration: 0.8 });
  }

  function handleMapPick(e) {
    const lat = Number(e.latlng.lat.toFixed(6));
    const lng = Number(e.latlng.lng.toFixed(6));
    if (editingLocationId !== null) {
      editLocationLat = lat;
      editLocationLng = lng;
    } else {
      newLocationLat = lat;
      newLocationLng = lng;
    }
  }

  function syncPickerMarker(lat, lng) {
    if (!map || !Number.isFinite(lat) || !Number.isFinite(lng)) return;

    if (!locationPickerMarker) {
      locationPickerMarker = L.marker([lat, lng], { icon: pinIcon, draggable: true }).addTo(map);
      locationPickerMarker.on("dragend", () => {
        const pos = locationPickerMarker.getLatLng();
        const roundedLat = Number(pos.lat.toFixed(6));
        const roundedLng = Number(pos.lng.toFixed(6));
        if (editingLocationId !== null) {
          editLocationLat = roundedLat;
          editLocationLng = roundedLng;
        } else {
          newLocationLat = roundedLat;
          newLocationLng = roundedLng;
        }
      });
    } else {
      locationPickerMarker.setLatLng([lat, lng]);
    }
  }

  function enableLocationPicker(lat, lng) {
    if (!map || pickerActive) return;
    pickerActive = true;
    markers.forEach((marker) => marker.remove());
    map.on("click", handleMapPick);
    syncPickerMarker(lat, lng);
  }

  function disableLocationPicker() {
    if (!map || !pickerActive) return;
    pickerActive = false;
    map.off("click", handleMapPick);
    locationPickerMarker?.remove();
    locationPickerMarker = null;
    renderMarkers();
  }

  $effect(() => {
    const adding = showAddLocationPanel;
    const editing = editingLocationId !== null;
    if (!map) return;
    if (adding) {
      enableLocationPicker(newLocationLat, newLocationLng);
    } else if (editing) {
      enableLocationPicker(editLocationLat, editLocationLng);
    } else {
      disableLocationPicker();
    }
  });

  $effect(() => {
    const lat = showAddLocationPanel ? newLocationLat : editLocationLat;
    const lng = showAddLocationPanel ? newLocationLng : editLocationLng;
    if (!pickerActive) return;
    syncPickerMarker(lat, lng);
  });

  function formatDate(isoDate) {
    const [year, month, day] = isoDate.split("-");
    return `${day}.${month}.${year}`;
  }

  function resetAddRoomForm() {
    showAddRoomForm = false;
    newRoomName = "";
    newRoomCapacity = 2;
    newRoomPrice = 200;
    newRoomAmenities = "";
    addRoomError = "";
    confirmDeleteRoomId = null;
  }

  function cancelEditRoom() {
    editingRoomId = null;
    editRoomError = "";
  }

  function startEditRoom(room) {
    resetAddRoomForm();
    editingRoomId = room.id;
    editRoomName = room.name;
    editRoomCapacity = room.capacity;
    editRoomPrice = room.price_per_night;
    editRoomAmenities = room.amenities;
    editRoomError = "";
  }

  async function saveEditRoom() {
    if (editingRoomId === null) return;
    if (!editRoomName.trim()) {
      editRoomError = "Podaj nazwę pokoju.";
      return;
    }

    savingRoom = true;
    editRoomError = "";
    try {
      const res = await fetch(`/api/rooms/${editingRoomId}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editRoomName.trim(),
          capacity: Number(editRoomCapacity),
          price_per_night: Number(editRoomPrice),
          amenities: editRoomAmenities.trim(),
        }),
      });
      if (res.ok) {
        const updatedRoom = await res.json();
        detailLocation = {
          ...detailLocation,
          rooms: detailLocation.rooms.map((room) => (room.id === updatedRoom.id ? updatedRoom : room)),
        };
        cancelEditRoom();
      } else {
        editRoomError = "Nie udało się zapisać zmian. Spróbuj ponownie.";
      }
    } finally {
      savingRoom = false;
    }
  }

  function cancelEditLocationDetails() {
    editingLocationId = null;
    editLocationError = "";
  }

  function startEditLocationDetails(location) {
    showAddLocationPanel = false;
    editingLocationId = location.id;
    editLocationName = location.name;
    editLocationAddress = location.address;
    editLocationDescription = location.description;
    editLocationLat = location.latitude;
    editLocationLng = location.longitude;
    editLocationError = "";
  }

  async function saveEditLocationDetails() {
    if (editingLocationId === null) return;
    if (!editLocationName.trim()) {
      editLocationError = "Podaj nazwę lokalizacji.";
      return;
    }

    savingLocationDetails = true;
    editLocationError = "";
    try {
      const res = await fetch(`/api/locations/${editingLocationId}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editLocationName.trim(),
          address: editLocationAddress.trim(),
          description: editLocationDescription.trim(),
          latitude: Number(editLocationLat),
          longitude: Number(editLocationLng),
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        locations = locations.map((location) => (location.id === updated.id ? updated : location));
        renderMarkers();
        cancelEditLocationDetails();
      } else {
        editLocationError = "Nie udało się zapisać zmian. Spróbuj ponownie.";
      }
    } finally {
      savingLocationDetails = false;
    }
  }

  async function openDetail(location) {
    detailLoading = true;
    resetAddRoomForm();
    cancelEditRoom();
    cancelEditLocationDetails();
    resetAddLocationForm();
    try {
      const res = await fetch(`/api/locations/${location.id}`, { credentials: "include" });
      if (res.ok) {
        detailLocation = await res.json();
        // Poczekaj aż animacja przesunięcia/zmiany rozmiaru mapy się zakończy,
        // zanim przeliczymy jej wymiary i dolecimy do budynku.
        setTimeout(() => {
          map?.invalidateSize();
          map?.flyTo([detailLocation.latitude, detailLocation.longitude], 15, { duration: 0.8 });
        }, LAYOUT_TRANSITION_MS);
      }
    } finally {
      detailLoading = false;
    }
  }

  function closeDetail() {
    detailLocation = null;
    resetAddRoomForm();
    cancelEditRoom();
    cancelEditLocationDetails();
    setTimeout(() => {
      map?.invalidateSize();
      map?.flyTo(POLAND_CENTER, POLAND_ZOOM, { duration: 0.8 });
    }, LAYOUT_TRANSITION_MS);
  }

  function toggleAddRoomForm() {
    cancelEditRoom();
    showAddRoomForm = !showAddRoomForm;
    addRoomError = "";
  }

  async function submitNewRoom() {
    if (!detailLocation) return;
    if (!newRoomName.trim()) {
      addRoomError = "Podaj nazwę pokoju.";
      return;
    }

    addingRoom = true;
    addRoomError = "";
    try {
      const res = await fetch(`/api/locations/${detailLocation.id}/rooms`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newRoomName.trim(),
          capacity: Number(newRoomCapacity),
          price_per_night: Number(newRoomPrice),
          amenities: newRoomAmenities.trim(),
        }),
      });
      if (res.ok) {
        const room = await res.json();
        detailLocation = { ...detailLocation, rooms: [...detailLocation.rooms, room] };
        resetAddRoomForm();
      } else {
        addRoomError = "Nie udało się dodać pokoju. Spróbuj ponownie.";
      }
    } finally {
      addingRoom = false;
    }
  }

  function toggleAddLocationPanel() {
    cancelEditLocationDetails();
    showAddLocationPanel = !showAddLocationPanel;
    addLocationError = "";
  }

  function resetAddLocationForm() {
    showAddLocationPanel = false;
    newLocationName = "";
    newLocationAddress = "";
    newLocationDescription = "";
    newLocationLat = 52.2297;
    newLocationLng = 21.0122;
    addLocationError = "";
  }

  async function submitNewLocation() {
    if (!newLocationName.trim()) {
      addLocationError = "Podaj nazwę lokalizacji.";
      return;
    }

    addingLocation = true;
    addLocationError = "";
    try {
      const res = await fetch("/api/locations", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newLocationName.trim(),
          address: newLocationAddress.trim(),
          description: newLocationDescription.trim(),
          latitude: Number(newLocationLat),
          longitude: Number(newLocationLng),
        }),
      });
      if (res.ok) {
        const location = await res.json();
        locations = [...locations, location];
        resetAddLocationForm();
      } else {
        addLocationError = "Nie udało się dodać lokalizacji. Spróbuj ponownie.";
      }
    } finally {
      addingLocation = false;
    }
  }

  function requestDeleteRoom(roomId) {
    confirmDeleteRoomId = roomId;
  }

  function cancelDeleteRoom() {
    confirmDeleteRoomId = null;
  }

  async function confirmDeleteRoom(roomId) {
    if (!detailLocation) return;
    deletingRoom = true;
    try {
      const res = await fetch(`/api/rooms/${roomId}`, { method: "DELETE", credentials: "include" });
      if (res.ok) {
        detailLocation = { ...detailLocation, rooms: detailLocation.rooms.filter((room) => room.id !== roomId) };
      }
    } finally {
      deletingRoom = false;
      confirmDeleteRoomId = null;
    }
  }

  onMount(() => {
    map = L.map(mapContainer, {
      center: POLAND_CENTER,
      zoom: POLAND_ZOOM,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    // Kontener może mieć jeszcze niepełny rozmiar tuż po pierwszym renderze.
    setTimeout(() => map?.invalidateSize(), 100);

    loadLocations();
  });

  onDestroy(() => {
    map?.remove();
  });
</script>

<div class="locations-page">
  <button class="back-link" onclick={onBack}><i class="fa-solid fa-arrow-left"></i> Wróć do panelu</button>

  <div class="page-header">
    <div class="page-header-text">
      <h1>Zarządzanie <span class="highlight">lokalizacjami</span></h1>
      <p>Przeglądaj obiekty na mapie i sprawdzaj ich dane.</p>
    </div>
  </div>

  {#if detailLocation}
    <button class="back-to-overview" onclick={closeDetail}>
      <i class="fa-solid fa-arrow-rotate-left"></i> Powrót do widoku ogólnego
    </button>
  {:else}
    <div class="list-actions-row">
      <button class="add-location-toggle" onclick={toggleAddLocationPanel}>
        <i class="fa-solid {showAddLocationPanel ? 'fa-xmark' : 'fa-plus'}"></i>
        {showAddLocationPanel ? "Anuluj" : "Dodaj lokalizację"}
      </button>
    </div>
  {/if}

  <div class="content-layout" class:detail-mode={!!detailLocation}>
    <div class="map-card">
      <div class="map-container" class:picking={showAddLocationPanel || editingLocationId !== null} bind:this={mapContainer}></div>
    </div>

    {#if !detailLocation}
      {#if showAddLocationPanel}
        <div
          class="add-location-panel"
          in:fly={{ x: -320, duration: 400, easing: cubicInOut }}
          out:fly={{ x: -320, duration: 400, easing: cubicInOut }}
        >
          <h3>Nowa lokalizacja</h3>
          <p class="add-location-hint">
            <i class="fa-solid fa-map-pin"></i> Kliknij na mapie, aby wskazać położenie obiektu.
          </p>
          <div class="add-location-form">
            <div class="form-row">
              <label for="new-location-name">Nazwa</label>
              <input id="new-location-name" type="text" placeholder="np. Apartamenty Centrum" bind:value={newLocationName} />
            </div>
            <div class="form-row">
              <label for="new-location-address">Adres</label>
              <input id="new-location-address" type="text" placeholder="np. ul. Kwiatowa 5, Warszawa" bind:value={newLocationAddress} />
            </div>
            <div class="form-row">
              <label for="new-location-description">Opis</label>
              <input id="new-location-description" type="text" placeholder="Krótki opis obiektu" bind:value={newLocationDescription} />
            </div>
            <div class="form-row form-row-split">
              <div>
                <label for="new-location-lat">Szerokość geogr.</label>
                <input id="new-location-lat" type="number" step="0.0001" min="-90" max="90" bind:value={newLocationLat} />
              </div>
              <div>
                <label for="new-location-lng">Długość geogr.</label>
                <input id="new-location-lng" type="number" step="0.0001" min="-180" max="180" bind:value={newLocationLng} />
              </div>
            </div>
            {#if addLocationError}
              <p class="add-room-error">{addLocationError}</p>
            {/if}
            <button class="add-room-submit" onclick={submitNewLocation} disabled={addingLocation}>
              {addingLocation ? "Dodawanie..." : "Dodaj lokalizację"}
            </button>
          </div>
        </div>
      {:else if editingLocationId !== null}
        <div
          class="add-location-panel"
          in:fly={{ x: -320, duration: 400, easing: cubicInOut }}
          out:fly={{ x: -320, duration: 400, easing: cubicInOut }}
        >
          <h3>Edytuj lokalizację</h3>
          <p class="add-location-hint">
            <i class="fa-solid fa-map-pin"></i> Kliknij na mapie lub przeciągnij znacznik, aby zmienić położenie obiektu.
          </p>
          <div class="add-location-form">
            <div class="form-row">
              <label for="edit-location-name">Nazwa</label>
              <input id="edit-location-name" type="text" bind:value={editLocationName} />
            </div>
            <div class="form-row">
              <label for="edit-location-address">Adres</label>
              <input id="edit-location-address" type="text" bind:value={editLocationAddress} />
            </div>
            <div class="form-row">
              <label for="edit-location-description">Opis</label>
              <input id="edit-location-description" type="text" bind:value={editLocationDescription} />
            </div>
            <div class="form-row form-row-split">
              <div>
                <label for="edit-location-lat">Szerokość geogr.</label>
                <input id="edit-location-lat" type="number" step="0.0001" min="-90" max="90" bind:value={editLocationLat} />
              </div>
              <div>
                <label for="edit-location-lng">Długość geogr.</label>
                <input id="edit-location-lng" type="number" step="0.0001" min="-180" max="180" bind:value={editLocationLng} />
              </div>
            </div>
            {#if editLocationError}
              <p class="add-room-error">{editLocationError}</p>
            {/if}
            <div class="edit-room-actions">
              <button class="room-delete-cancel" onclick={cancelEditLocationDetails} disabled={savingLocationDetails}>
                Anuluj
              </button>
              <button class="add-room-submit" onclick={saveEditLocationDetails} disabled={savingLocationDetails}>
                {savingLocationDetails ? "Zapisywanie..." : "Zapisz zmiany"}
              </button>
            </div>
          </div>
        </div>
      {:else}
        <div
          class="list-panel"
          in:fly={{ x: 320, duration: 400, easing: cubicInOut }}
          out:fly={{ x: 320, duration: 400, easing: cubicInOut }}
        >
          <div class="search-bar">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input type="text" placeholder="Szukaj lokalizacji..." bind:value={searchQuery} />
          </div>

          {#if !loading}
            <div class="location-list">
              {#each filteredLocations as location (location.id)}
                <div class="location-item">
                  <button class="location-item-main" onclick={() => focusLocation(location)}>
                    <span class="item-blob" aria-hidden="true"></span>
                    <div class="item-icon"><i class="fa-solid fa-building"></i></div>
                    <div class="item-text">
                      <h3>{location.name}</h3>
                      <p>{location.address}</p>
                    </div>
                  </button>
                  <button class="room-edit-btn" onclick={() => startEditLocationDetails(location)} aria-label="Edytuj lokalizację">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <button class="details-btn" onclick={() => openDetail(location)}>
                    Szczegóły <i class="fa-solid fa-chevron-right"></i>
                  </button>
                </div>
              {/each}
              {#if filteredLocations.length === 0}
                <p class="detail-placeholder">Brak wyników.</p>
              {/if}
            </div>
          {/if}
        </div>
      {/if}
    {:else}
      <div class="detail-left" transition:fade={{ duration: 250, delay: 150, easing: cubicInOut }}>
        <div class="detail-card">
          <h2>{detailLocation.name}</h2>
          <p class="detail-address"><i class="fa-solid fa-location-dot"></i> {detailLocation.address}</p>
          {#if detailLocation.description}
            <p class="detail-description">{detailLocation.description}</p>
          {/if}
        </div>

        <div class="detail-card rooms-card">
          <h3>Pokoje</h3>
          {#if editingRoomId !== null}
            <div class="edit-room-form" transition:slide={{ duration: 250, easing: cubicInOut }}>
              <div class="form-row">
                <label for="edit-room-name">Nazwa</label>
                <input id="edit-room-name" type="text" placeholder="np. Pokój Deluxe" bind:value={editRoomName} />
              </div>
              <div class="form-row form-row-split">
                <div>
                  <label for="edit-room-capacity">Ilość osób</label>
                  <input id="edit-room-capacity" type="number" min="1" max="20" bind:value={editRoomCapacity} />
                </div>
                <div>
                  <label for="edit-room-price">Cena za noc</label>
                  <input id="edit-room-price" type="number" min="0" step="10" bind:value={editRoomPrice} />
                </div>
              </div>
              <div class="form-row">
                <label for="edit-room-amenities">Udogodnienia</label>
                <input
                  id="edit-room-amenities"
                  type="text"
                  placeholder="np. Wi-Fi, TV, balkon"
                  bind:value={editRoomAmenities}
                />
              </div>
              {#if editRoomError}
                <p class="add-room-error">{editRoomError}</p>
              {/if}
              <div class="edit-room-actions">
                <button class="room-delete-cancel" onclick={cancelEditRoom} disabled={savingRoom}>
                  Anuluj
                </button>
                <button class="add-room-submit" onclick={saveEditRoom} disabled={savingRoom}>
                  {savingRoom ? "Zapisywanie..." : "Zapisz zmiany"}
                </button>
              </div>
            </div>
          {:else}
          <div class="room-list">
            {#each detailLocation.rooms as room (room.id)}
              <div class="room-item">
                {#if confirmDeleteRoomId === room.id}
                  <div class="room-delete-overlay" transition:fade={{ duration: 180, easing: cubicInOut }}>
                    <span class="room-delete-blob" aria-hidden="true"></span>
                    <p>Usunąć ten pokój?</p>
                    <div class="room-delete-overlay-actions">
                      <button class="room-delete-cancel" onclick={cancelDeleteRoom} disabled={deletingRoom}>
                        Anuluj
                      </button>
                      <button
                        class="room-delete-confirm"
                        onclick={() => confirmDeleteRoom(room.id)}
                        disabled={deletingRoom}
                      >
                        {deletingRoom ? "Usuwanie..." : "Potwierdź"}
                      </button>
                    </div>
                  </div>
                {/if}
                <div class="room-item-main">
                  <span class="room-status-dot" class:occupied={!!room.current_reservation}></span>
                  <div>
                    <h4>{room.name}</h4>
                    <p>{room.capacity} os. &middot; {room.price_per_night.toFixed(0)} zł / noc</p>
                    {#if room.amenities}
                      <p class="room-amenities">{room.amenities}</p>
                    {/if}
                  </div>
                </div>
                <div class="room-item-actions">
                  <span class="room-status-label" class:occupied={!!room.current_reservation}>
                    {room.current_reservation ? "Zajęty" : "Wolny"}
                  </span>
                  <button class="room-edit-btn" onclick={() => startEditRoom(room)} aria-label="Edytuj pokój">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <button class="room-delete-btn" onclick={() => requestDeleteRoom(room.id)} aria-label="Usuń pokój">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              </div>
            {/each}
            {#if detailLocation.rooms.length === 0}
              <p class="detail-placeholder">Brak pokoi.</p>
            {/if}
          </div>
          {/if}
        </div>

        <div class="detail-card add-room-card">
          <button class="add-room-toggle" onclick={toggleAddRoomForm}>
            <i class="fa-solid {showAddRoomForm ? 'fa-minus' : 'fa-plus'}"></i>
            {showAddRoomForm ? "Anuluj" : "Dodaj pokój"}
          </button>

          {#if showAddRoomForm}
            <div class="add-room-form" transition:slide={{ duration: 250, easing: cubicInOut }}>
              <div class="form-row">
                <label for="new-room-name">Nazwa</label>
                <input id="new-room-name" type="text" placeholder="np. Pokój Deluxe" bind:value={newRoomName} />
              </div>
              <div class="form-row form-row-split">
                <div>
                  <label for="new-room-capacity">Ilość osób</label>
                  <input id="new-room-capacity" type="number" min="1" max="20" bind:value={newRoomCapacity} />
                </div>
                <div>
                  <label for="new-room-price">Cena za noc</label>
                  <input id="new-room-price" type="number" min="0" step="10" bind:value={newRoomPrice} />
                </div>
              </div>
              <div class="form-row">
                <label for="new-room-amenities">Udogodnienia</label>
                <input
                  id="new-room-amenities"
                  type="text"
                  placeholder="np. Wi-Fi, TV, balkon"
                  bind:value={newRoomAmenities}
                />
              </div>
              {#if addRoomError}
                <p class="add-room-error">{addRoomError}</p>
              {/if}
              <button class="add-room-submit" onclick={submitNewRoom} disabled={addingRoom}>
                {addingRoom ? "Dodawanie..." : "Dodaj pokój"}
              </button>
            </div>
          {/if}
        </div>
      </div>

      <div class="reservation-panel" transition:fade={{ duration: 250, delay: 150, easing: cubicInOut }}>
        <h3>Aktualna rezerwacja</h3>
        {#if currentReservations.length > 0}
          <div class="reservation-list">
            {#each currentReservations as room (room.id)}
              <div class="reservation-item">
                <div class="reservation-item-main">
                  <i class="fa-solid fa-user"></i>
                  <div>
                    <h4>{room.current_reservation.guest_name}</h4>
                    <p>Pokój: {room.name}</p>
                  </div>
                </div>
                <span class="reservation-dates">
                  {formatDate(room.current_reservation.check_in)} – {formatDate(room.current_reservation.check_out)}
                </span>
              </div>
            {/each}
          </div>
        {:else}
          <p class="detail-placeholder">Brak aktualnej rezerwacji.</p>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .locations-page {
    width: 100%;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: #666;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 24px;
    transition: color 0.2s;
  }

  .back-link:hover {
    color: var(--pink);
  }

  .page-header {
    margin-bottom: 28px;
  }

  .page-header-text h1 {
    font-size: 34px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .page-header-text p {
    color: #666;
    font-size: 16px;
  }

  .back-to-overview {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: 1px solid #eaeaea;
    border-radius: 8px;
    padding: 8px 14px;
    color: var(--pink);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 16px;
    transition: background 0.2s ease, border-color 0.2s ease;
  }

  .back-to-overview:hover {
    background: rgba(255, 82, 162, 0.08);
    border-color: var(--pink);
  }

  .content-layout {
    position: relative;
    z-index: 0;
    height: 600px;
    overflow: hidden;
  }

  .list-actions-row {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 16px;
  }

  .add-location-toggle {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: 1px solid #eaeaea;
    border-radius: 8px;
    padding: 9px 16px;
    color: var(--pink);
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease;
  }

  .add-location-toggle:hover {
    background: rgba(255, 82, 162, 0.08);
    border-color: var(--pink);
  }

  .add-location-panel {
    position: absolute;
    z-index: -1;
    top: 0;
    left: calc(50% + 12px);
    width: calc(50% - 12px);
    min-width: 0;
    display: flex;
    flex-direction: column;
    height: 600px;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 20px 22px;
    overflow-y: auto;
  }

  .add-location-panel h3 {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .add-location-hint {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #666;
    font-size: 13px;
  }

  .add-location-hint i {
    color: var(--pink);
  }

  .add-location-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid #eaeaea;
  }

  .map-card {
    position: absolute;
    z-index: 0;
    top: 0;
    left: 0;
    width: calc(50% - 12px);
    height: 600px;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    overflow: hidden;
    transition: top 0.5s cubic-bezier(0.4, 0, 0.2, 1), left 0.5s cubic-bezier(0.4, 0, 0.2, 1),
      width 0.5s cubic-bezier(0.4, 0, 0.2, 1), height 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .content-layout.detail-mode .map-card {
    top: 0;
    left: calc(50% + 12px);
    width: calc(50% - 12px);
    height: 260px;
  }

  .map-container {
    width: 100%;
    height: 100%;
  }

  .map-container.picking {
    cursor: crosshair;
  }

  .list-panel {
    position: absolute;
    top: 0;
    left: calc(50% + 12px);
    width: calc(50% - 12px);
    min-width: 0;
    display: flex;
    flex-direction: column;
    height: 600px;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 20px;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #f5f5f5;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 16px;
    flex-shrink: 0;
  }

  .search-bar i {
    color: #999;
    font-size: 14px;
  }

  .search-bar input {
    flex: 1;
    border: none;
    background: none;
    outline: none;
    font-size: 14px;
    font-family: inherit;
    color: var(--text-dark);
  }

  .location-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-right: 4px;
  }

  .location-item {
    position: relative;
    flex-shrink: 0;
    height: 74px;
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 12px 10px 12px 14px;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  }

  .location-item:hover {
    transform: translateX(4px);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.06);
    border-color: var(--pink);
  }

  .location-item-main {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 14px;
    flex: 1;
    min-width: 0;
    text-align: left;
    background: none;
    border: none;
    padding: 0;
    font: inherit;
    color: inherit;
    cursor: pointer;
  }

  .details-btn {
    position: relative;
    z-index: 1;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: 1px solid #eaeaea;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--pink);
    white-space: nowrap;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease;
  }

  .details-btn:hover {
    background: rgba(255, 82, 162, 0.08);
    border-color: var(--pink);
  }

  .details-btn i {
    font-size: 10px;
  }

  .item-blob {
    position: absolute;
    top: -20px;
    left: -20px;
    width: 70px;
    height: 70px;
    border-radius: 50%;
    background: var(--pink);
    filter: blur(18px);
    opacity: 0.25;
    pointer-events: none;
  }

  .item-icon {
    position: relative;
    z-index: 1;
    flex-shrink: 0;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: rgba(255, 82, 162, 0.1);
    color: var(--pink);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
  }

  .item-text {
    position: relative;
    z-index: 1;
    min-width: 0;
  }

  .item-text h3 {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .item-text p {
    font-size: 12.5px;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .detail-placeholder {
    color: #999;
    font-size: 15px;
  }

  .detail-left {
    position: absolute;
    top: 0;
    left: 0;
    width: calc(50% - 12px);
    height: 600px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    min-width: 0;
  }

  .detail-card {
    flex-shrink: 0;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 20px 22px;
  }

  .detail-card h2 {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .detail-card h3 {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 12px;
  }

  .detail-address {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #666;
    font-size: 13.5px;
    margin-bottom: 10px;
  }

  .detail-address i {
    color: var(--pink);
  }

  .detail-description {
    color: #444;
    font-size: 14px;
    line-height: 1.5;
  }

  .reservation-panel {
    position: absolute;
    top: 280px;
    left: calc(50% + 12px);
    width: calc(50% - 12px);
    height: 320px;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 20px 22px;
    overflow: hidden;
  }

  .reservation-panel h3 {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 12px;
    flex-shrink: 0;
  }

  .reservation-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-right: 4px;
  }

  .reservation-item {
    flex-shrink: 0;
    height: 68px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 10px 14px;
    overflow: hidden;
  }

  .reservation-item-main {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .reservation-item-main > i {
    flex-shrink: 0;
    color: var(--pink);
    font-size: 14px;
  }

  .reservation-item-main > div {
    min-width: 0;
  }

  .reservation-item-main h4 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .reservation-item-main p {
    font-size: 12.5px;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .reservation-dates {
    flex-shrink: 0;
    font-size: 12px;
    color: #666;
    white-space: nowrap;
  }

  .rooms-card {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .room-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-right: 4px;
  }

  .room-item {
    position: relative;
    flex-shrink: 0;
    height: 92px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 12px 14px;
    overflow: hidden;
  }

  .room-delete-overlay {
    position: absolute;
    inset: 0;
    z-index: 2;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: flex-end;
    gap: 20px;
    padding: 0 18px;
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    border-radius: 10px;
    overflow: hidden;
  }

  .room-delete-blob {
    position: absolute;
    top: 50%;
    left: -20px;
    transform: translateY(-50%);
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: var(--pink);
    filter: blur(20px);
    opacity: 0.4;
    pointer-events: none;
    z-index: 0;
  }

  .room-delete-overlay p {
    position: relative;
    z-index: 1;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-dark);
    white-space: nowrap;
  }

  .room-delete-overlay-actions {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .room-delete-cancel,
  .room-delete-confirm {
    border: none;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: opacity 0.2s ease, background 0.2s ease;
  }

  .room-delete-cancel {
    background: none;
    color: #666;
  }

  .room-delete-cancel:hover {
    color: var(--text-dark);
  }

  .room-delete-confirm {
    background: var(--pink);
    color: white;
  }

  .room-delete-confirm:hover {
    opacity: 0.9;
  }

  .room-delete-cancel:disabled,
  .room-delete-confirm:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .room-item-main {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .room-item-main > div {
    min-width: 0;
  }

  .room-status-dot {
    flex-shrink: 0;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #34c759;
  }

  .room-status-dot.occupied {
    background: var(--pink);
  }

  .room-item-main h4 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .room-item-main p {
    font-size: 12.5px;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .room-amenities {
    margin-top: 2px;
    font-size: 11.5px;
    color: #999;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .room-item-actions {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .room-status-label {
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
    color: #1e9e46;
  }

  .room-status-label.occupied {
    color: var(--pink);
  }

  .room-edit-btn,
  .room-delete-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: none;
    border: 1px solid #eaeaea;
    border-radius: 8px;
    color: #999;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  }

  .room-edit-btn:hover {
    background: rgba(255, 82, 162, 0.08);
    border-color: var(--pink);
    color: var(--pink);
  }

  .room-delete-btn:hover {
    background: rgba(220, 38, 38, 0.08);
    border-color: #dc2626;
    color: #dc2626;
  }

  .add-room-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    background: none;
    border: 1px dashed #d1d5db;
    border-radius: 10px;
    padding: 10px 14px;
    color: var(--pink);
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease;
  }

  .add-room-toggle:hover {
    background: rgba(255, 82, 162, 0.06);
    border-color: var(--pink);
  }

  .add-room-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid #eaeaea;
  }

  .edit-room-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .edit-room-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  .edit-room-actions .room-delete-cancel {
    border: 1px solid #eaeaea;
    border-radius: 8px;
    padding: 10px 14px;
  }

  .edit-room-actions .add-room-submit {
    width: auto;
  }

  .form-row {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .form-row-split {
    flex-direction: row;
    gap: 12px;
  }

  .form-row-split > div {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .add-room-form label,
  .add-location-form label,
  .edit-room-form label {
    font-size: 12px;
    font-weight: 600;
    color: #666;
  }

  .add-room-form input,
  .add-location-form input,
  .edit-room-form input {
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 13.5px;
    font-family: inherit;
    color: var(--text-dark);
    outline: none;
    transition: border-color 0.2s ease;
  }

  .add-room-form input:focus,
  .add-location-form input:focus,
  .edit-room-form input:focus {
    border-color: var(--pink);
  }

  .add-room-error {
    color: #dc2626;
    font-size: 12.5px;
  }

  .add-room-submit {
    background: var(--pink);
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    color: white;
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .add-room-submit:hover {
    opacity: 0.9;
  }

  .add-room-submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  :global(.location-pin) {
    background: transparent;
    border: none;
  }

  :global(.pin-body) {
    width: 32px;
    height: 32px;
    background: var(--pink);
    border: 3px solid white;
    border-radius: 50% 50% 50% 0;
    transform: rotate(-45deg);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  :global(.pin-body i) {
    transform: rotate(45deg);
    color: white;
    font-size: 13px;
  }

  @media (max-width: 900px) {
    .content-layout {
      position: static;
      height: auto;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .map-card {
      position: static;
      width: 100%;
      height: 340px;
      transition: none;
    }

    .content-layout.detail-mode .map-card {
      width: 100%;
      height: 260px;
    }

    .list-panel,
    .add-location-panel,
    .detail-left,
    .reservation-panel {
      position: static;
      width: 100%;
    }

    .list-panel {
      height: 400px;
    }

    .add-location-panel {
      height: auto;
      overflow-y: visible;
    }

    .detail-left {
      height: auto;
      max-height: none;
      overflow-y: visible;
    }

    .reservation-panel {
      height: auto;
    }
  }
</style>
