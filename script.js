document.addEventListener('DOMContentLoaded', () => {
    const monthSelect = document.getElementById('month');
    const yearInput = document.getElementById('year');
    const showCalendarButton = document.getElementById('show-calendar');
    const calendarContainer = document.getElementById('calendar-container');
    const selectedFlightDetails = document.getElementById('selected-flight-details');

    // Voorbeeld vluchtgegevens (normaal gesproken van een API)
    // Sleutels zijn in 'YYYY-MM-DD' formaat
    // Waarden kunnen objecten zijn met meer details, voor nu alleen prijs
    const mockFlightData = {
        "2024-07-15": { price: 120, airline: "Ryanair", from: "AMS", to: "BCN" },
        "2024-07-16": { price: 110, airline: "Vueling", from: "EIN", to: "MAD" },
        "2024-07-17": { price: 135, airline: "KLM", from: "AMS", to: "VLC" },
        "2024-07-22": { price: 95, airline: "Transavia", from: "RTM", to: "AGP" }, // Goedkoopste voorbeeld
        "2024-07-23": { price: 105, airline: "Iberia Express", from: "AMS", to: "SVQ" },
        "2024-08-05": { price: 150, airline: "KLM", from: "AMS", to: "MAD" },
        "2024-08-06": { price: 140, airline: "Transavia", from: "EIN", to: "BCN" },
    };


    // Stel huidige maand en jaar in als standaard
    const today = new Date();
    monthSelect.value = today.getMonth();
    yearInput.value = today.getFullYear();

    showCalendarButton.addEventListener('click', generateCalendar);

    function generateCalendar() {
        const month = parseInt(monthSelect.value);
        const year = parseInt(yearInput.value);

        if (isNaN(year) || year < 2000) {
            alert("Voer een geldig jaar in.");
            return;
        }

        calendarContainer.innerHTML = ''; // Leeg de vorige kalender

        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const firstDayOfMonth = new Date(year, month, 1).getDay(); // 0 (Zondag) - 6 (Zaterdag)

        // Aanpassing voor Nederlandse weekstart (Maandag)
        const adjustedFirstDay = (firstDayOfMonth === 0) ? 6 : firstDayOfMonth - 1;

        const calendarTable = document.createElement('table');
        calendarTable.classList.add('calendar');

        // Kalender header (dagen van de week)
        const headerRow = calendarTable.insertRow();
        const daysOfWeek = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Za', 'Zo'];
        daysOfWeek.forEach(day => {
            const cell = headerRow.insertCell();
            cell.textContent = day;
        });

        // Kalender dagen
        let date = 1;
        for (let i = 0; i < 6; i++) { // Maximaal 6 rijen voor een maand
            const row = calendarTable.insertRow();
            for (let j = 0; j < 7; j++) { // 7 dagen per week
                const cell = row.insertCell();
                if (i === 0 && j < adjustedFirstDay) {
                    // Lege cellen voor de start van de maand
                    cell.classList.add('empty');
                } else if (date > daysInMonth) {
                    // Lege cellen na het einde van de maand
                    cell.classList.add('empty');
                } else {
                    cell.textContent = date;
                    cell.classList.add('date-cell');
                    const currentDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(date).padStart(2, '0')}`;
                    cell.dataset.date = currentDateStr;

                    // Voeg vluchtinformatie toe indien beschikbaar
                    if (mockFlightData[currentDateStr]) {
                        const flight = mockFlightData[currentDateStr];
                        const priceElement = document.createElement('div');
                        priceElement.classList.add('price');
                        priceElement.textContent = `€${flight.price}`;
                        cell.appendChild(priceElement);
                        cell.classList.add('has-flight');

                        // Data attributen voor vlucht details
                        cell.dataset.airline = flight.airline;
                        cell.dataset.from = flight.from;
                        cell.dataset.to = flight.to;
                        cell.dataset.price = flight.price;
                    }

                    cell.addEventListener('click', () => {
                        if (cell.classList.contains('has-flight')) {
                            selectedFlightDetails.innerHTML = `
                                <strong>Datum:</strong> ${cell.dataset.date}<br>
                                <strong>Prijs:</strong> €${cell.dataset.price}<br>
                                <strong>Luchtvaartmaatschappij:</strong> ${cell.dataset.airline}<br>
                                <strong>Van:</strong> ${cell.dataset.from}<br>
                                <strong>Naar:</strong> ${cell.dataset.to}
                            `;
                        } else {
                            selectedFlightDetails.textContent = `Geen vluchtinformatie voor ${cell.dataset.date}.`;
                        }
                    });
                    date++;
                }
            }
            if (date > daysInMonth && i < 5) { // Stop met rijen maken als alle dagen zijn geplaatst en het niet de laatste iteratie is
                 if (calendarTable.rows[calendarTable.rows.length -1 ].cells[0].classList.contains('empty') &&
                    calendarTable.rows[calendarTable.rows.length -1 ].cells[1].classList.contains('empty') &&
                    calendarTable.rows[calendarTable.rows.length -1 ].cells[2].classList.contains('empty') &&
                    calendarTable.rows[calendarTable.rows.length -1 ].cells[3].classList.contains('empty') &&
                    calendarTable.rows[calendarTable.rows.length -1 ].cells[4].classList.contains('empty') &&
                    calendarTable.rows[calendarTable.rows.length -1 ].cells[5].classList.contains('empty') &&
                    calendarTable.rows[calendarTable.rows.length -1 ].cells[6].classList.contains('empty') ) {
                        calendarTable.deleteRow(calendarTable.rows.length -1);
                    }
            }
            if (date > daysInMonth && i === 5 && row.cells[0].textContent === '') { // Verwijder laatste rij als deze helemaal leeg is
                 calendarTable.deleteRow(i+1); // +1 omdat de header ook een rij is
            }
        }
        calendarContainer.appendChild(calendarTable);
        highlightCheapestFlights(year, month);
    }

    function highlightCheapestFlights(year, month) {
        let minPrice = Infinity;
        const currentMonthStr = `${year}-${String(month + 1).padStart(2, '0')}`;

        // Vind de minimum prijs voor de huidige maand in de mock data
        for (const dateStr in mockFlightData) {
            if (dateStr.startsWith(currentMonthStr)) {
                if (mockFlightData[dateStr].price < minPrice) {
                    minPrice = mockFlightData[dateStr].price;
                }
            }
        }

        // Markeer de cellen met de goedkoopste prijs
        if (minPrice !== Infinity) {
            const dateCells = calendarContainer.querySelectorAll('.date-cell.has-flight');
            dateCells.forEach(cell => {
                const cellPrice = parseFloat(cell.dataset.price);
                if (cellPrice === minPrice) {
                    cell.classList.add('cheapest');
                } else {
                    cell.classList.remove('cheapest'); // Zorg dat oude markeringen weg zijn
                }
            });
        }
    }

    // Genereer kalender bij laden van de pagina
    generateCalendar();
});
