document.addEventListener('DOMContentLoaded', () => {
    const mediumSelect = document.getElementById('medium');
    const calculationTypeVolume = document.getElementById('calcTypeVolume');
    const calculationTypePower = document.getElementById('calcTypeVermogen');
    const volumeInputsDiv = document.getElementById('volumeInputs');
    const powerInputsDiv = document.getElementById('powerInputs');
    const flowRateInput = document.getElementById('flowRate');
    const flowRateUnitSelect = document.getElementById('flowRateUnit');
    const powerInput = document.getElementById('power');

    const waterSpecificInputsDiv = document.getElementById('waterSpecificInputs');
    const gasSpecificInputsDiv = document.getElementById('gasSpecificInputs');
    const steamSpecificInputsDiv = document.getElementById('steamSpecificInputs');

    const velocityInput = document.getElementById('velocity');
    const deltaTInput = document.getElementById('deltaT');
    const calorificValueInput = document.getElementById('calorificValue');
    const steamPressureInput = document.getElementById('steamPressure');

    const calculateButton = document.getElementById('calculateButton');
    const printButton = document.getElementById('printButton');
    const resultSectionDiv = document.getElementById('resultSection');
    const resultDiameterSpan = document.getElementById('resultDiameter');
    const flowRateResultP = document.getElementById('flowRateResult');
    const calculatedFlowRateSpan = document.getElementById('calculatedFlowRate');
    const massFlowRateResultP = document.getElementById('massFlowRateResult');
    const calculatedMassFlowRateSpan = document.getElementById('calculatedMassFlowRate');

    const defaults = {
        water: { velocity: 1.5, deltaT: 20 },
        lucht: { velocity: 5 },
        gas: { velocity: 15, calorificValue: 31.65 }, // MJ/Nm³
        stoom: { velocity: 25, pressure: 5 } // barg
    };

    const RHO_WATER = 1000; // kg/m³
    const CP_WATER = 4.186; // kJ/kgK

    function updateInputVisibility() {
        const medium = mediumSelect.value;
        const calcType = document.querySelector('input[name="calculationType"]:checked').value;

        waterSpecificInputsDiv.style.display = 'none';
        gasSpecificInputsDiv.style.display = 'none';
        steamSpecificInputsDiv.style.display = 'none';
        document.querySelectorAll('.steam-only').forEach(el => el.style.display = 'none');

        velocityInput.value = defaults[medium].velocity;

        if (calcType === 'volume') {
            volumeInputsDiv.style.display = 'block';
            powerInputsDiv.style.display = 'none';
            if (medium === 'stoom') {
                document.querySelectorAll('.steam-only').forEach(el => el.style.display = 'inline');
                if (flowRateUnitSelect.value === 'kg/h') {
                    steamSpecificInputsDiv.style.display = 'block';
                    steamPressureInput.value = defaults.stoom.pressure;
                }
            }
        } else { // calcType === 'vermogen'
            volumeInputsDiv.style.display = 'none';
            powerInputsDiv.style.display = 'block';
            if (medium === 'water') {
                waterSpecificInputsDiv.style.display = 'block';
                deltaTInput.value = defaults.water.deltaT;
            } else if (medium === 'gas') {
                gasSpecificInputsDiv.style.display = 'block';
                calorificValueInput.value = defaults.gas.calorificValue;
            } else if (medium === 'stoom') {
                steamSpecificInputsDiv.style.display = 'block';
                steamPressureInput.value = defaults.stoom.pressure;
            } else if (medium === 'lucht') {
                powerInputsDiv.style.display = 'none';
                alert("Vermogen-gebaseerde berekening voor lucht is niet geïmplementeerd in deze simpele versie. Kies Volume/Debiet.");
                calculationTypeVolume.checked = true;
                updateInputVisibility(); // Recursive call to refresh UI based on new selection
                return;
            }
        }
    }

    function getFlowRateInM3s() {
        const flow = parseFloat(flowRateInput.value);
        const unit = flowRateUnitSelect.value;
        if (isNaN(flow) || flow < 0) {
            alert("Voer een geldig, niet-negatief debiet in.");
            return NaN;
        }
        if (unit === 'm3/h') return flow / 3600;
        if (unit === 'l/s') return flow / 1000;
        if (unit === 'l/min') return flow / 60000;
        return NaN; // Should not happen if kg/h is handled separately
    }

    function calculateDiameter() {
        resultSectionDiv.style.display = 'none';
        resultDiameterSpan.textContent = '--';
        flowRateResultP.style.display = 'none';
        massFlowRateResultP.style.display = 'none';

        const medium = mediumSelect.value;
        const calcType = document.querySelector('input[name="calculationType"]:checked').value;
        const velocity = parseFloat(velocityInput.value);

        if (isNaN(velocity) || velocity <= 0) {
            alert("Voer een geldige stroomsnelheid in (groter dan 0).");
            return;
        }

        let Q_m3s = NaN;
        let m_kgs = NaN;

        if (calcType === 'volume') {
            if (medium === 'stoom' && flowRateUnitSelect.value === 'kg/h') {
                const massFlow_kgh = parseFloat(flowRateInput.value);
                if (isNaN(massFlow_kgh) || massFlow_kgh < 0) {
                    alert("Voer een geldig, niet-negatief massadebiet in voor stoom.");
                    return;
                }
                m_kgs = massFlow_kgh / 3600;
                const pressure_barg = parseFloat(steamPressureInput.value);
                if (isNaN(pressure_barg) || pressure_barg < 0) {
                    alert("Voer een geldige, niet-negatieve stoomdruk in.");
                    return;
                }
                let rho_stoom_approx;
                if (pressure_barg <= 1) rho_stoom_approx = 1 / 0.885;
                else if (pressure_barg <= 3) rho_stoom_approx = 1 / 0.462;
                else if (pressure_barg <= 5) rho_stoom_approx = 1 / 0.315;
                else if (pressure_barg <= 7) rho_stoom_approx = 1 / 0.240;
                else rho_stoom_approx = 1 / 0.194;

                Q_m3s = (rho_stoom_approx && m_kgs > 0) ? m_kgs / rho_stoom_approx : (m_kgs === 0 ? 0 : NaN);
                if (isNaN(Q_m3s)) {
                     alert("Kon stoomdichtheid niet bepalen of ongeldig massadebiet.");
                     return;
                }
                calculatedMassFlowRateSpan.textContent = m_kgs.toFixed(4);
                massFlowRateResultP.style.display = 'block';
            } else {
                Q_m3s = getFlowRateInM3s();
                if (isNaN(Q_m3s)) return; // Alert is handled in getFlowRateInM3s
            }
        } else { // calcType === 'vermogen'
            const P_kW = parseFloat(powerInput.value);
            if (isNaN(P_kW) || P_kW <= 0) {
                alert("Voer een geldig vermogen in (groter dan 0).");
                return;
            }

            if (medium === 'water') {
                const deltaT = parseFloat(deltaTInput.value);
                if (isNaN(deltaT) || deltaT === 0) {
                    alert("Voer een geldig temperatuurverschil in (niet 0).");
                    return;
                }
                Q_m3s = P_kW / (RHO_WATER * CP_WATER * deltaT);
            } else if (medium === 'gas') {
                const H_u_gas_MJ_m3 = parseFloat(calorificValueInput.value);
                if (isNaN(H_u_gas_MJ_m3) || H_u_gas_MJ_m3 <= 0) {
                    alert("Voer een geldige verbrandingswaarde in (groter dan 0).");
                    return;
                }
                const H_u_gas_kJ_m3 = H_u_gas_MJ_m3 * 1000;
                const ETA_BRANDER = 0.9; // Assume 90% efficiency
                Q_m3s = P_kW / (H_u_gas_kJ_m3 * ETA_BRANDER);
            } else if (medium === 'stoom') {
                const pressure_barg_steam = parseFloat(steamPressureInput.value);
                 if (isNaN(pressure_barg_steam) || pressure_barg_steam < 0) {
                    alert("Voer een geldige stoomdruk in (niet negatief).");
                    return;
                }
                let h_fg_stoom_approx;
                if (pressure_barg_steam <= 1) h_fg_stoom_approx = 2202;
                else if (pressure_barg_steam <= 3) h_fg_stoom_approx = 2133;
                else if (pressure_barg_steam <= 5) h_fg_stoom_approx = 2085;
                else if (pressure_barg_steam <= 7) h_fg_stoom_approx = 2047;
                else h_fg_stoom_approx = 2015;

                if (h_fg_stoom_approx === 0) {
                     alert("Fout bij het bepalen van stoom eigenschappen (enthalpie)."); return;
                }
                m_kgs = P_kW / h_fg_stoom_approx;
                calculatedMassFlowRateSpan.textContent = m_kgs.toFixed(4);
                massFlowRateResultP.style.display = 'block';

                let rho_stoom_approx_power;
                if (pressure_barg_steam <= 1) rho_stoom_approx_power = 1 / 0.885;
                else if (pressure_barg_steam <= 3) rho_stoom_approx_power = 1 / 0.462;
                else if (pressure_barg_steam <= 5) rho_stoom_approx_power = 1 / 0.315;
                else if (pressure_barg_steam <= 7) rho_stoom_approx_power = 1 / 0.240;
                else rho_stoom_approx_power = 1 / 0.194;

                Q_m3s = (rho_stoom_approx_power && m_kgs > 0) ? m_kgs / rho_stoom_approx_power : (m_kgs === 0 ? 0 : NaN);
                 if (isNaN(Q_m3s)) {
                     alert("Kon stoomdichtheid niet bepalen voor vermogensberekening.");
                     return;
                }
            }
        }

        if (isNaN(Q_m3s)) {
            // This case should ideally be caught by earlier checks.
            // If Q_m3s is NaN here, it means an unhandled case or logic error in flow calculation.
            alert("Kon debiet niet berekenen. Controleer alle invoerwaardes.");
            preparePrintData(); // Update print summary with no result
            return;
        }

        calculatedFlowRateSpan.textContent = Q_m3s.toFixed(5);
        flowRateResultP.style.display = 'block';

        if (Q_m3s > 0 && velocity > 0) {
            const area_m2 = Q_m3s / velocity;
            const diameter_m = Math.sqrt((4 * area_m2) / Math.PI);
            resultDiameterSpan.textContent = (diameter_m * 1000).toFixed(2);
            resultSectionDiv.style.display = 'block';
        } else if (Q_m3s === 0 && velocity > 0) {
            resultDiameterSpan.textContent = (0).toFixed(2);
            resultSectionDiv.style.display = 'block';
        } else {
            // Velocity is <= 0 (already alerted) or Q_m3s < 0 (should be caught)
            // No further alert needed here as prior checks should handle it.
        }
        preparePrintData();
    }

    function preparePrintData() {
        const existingPrintSummary = document.getElementById('printSummary');
        if (existingPrintSummary) {
            existingPrintSummary.remove();
        }

        const printSummaryDiv = document.createElement('div');
        printSummaryDiv.id = 'printSummary';
        printSummaryDiv.classList.add('print-input-summary');

        const mediumVal = mediumSelect.options[mediumSelect.selectedIndex].text;
        const calcTypeVal = document.querySelector('input[name="calculationType"]:checked').value;
        const velocityVal = velocityInput.value;

        printSummaryDiv.innerHTML += `<p><strong>Medium:</strong> ${mediumVal}</p>`;
        printSummaryDiv.innerHTML += `<p><strong>Berekeningstype:</strong> ${calcTypeVal === 'volume' ? 'Volume/Debiet' : 'Vermogen'}</p>`;

        if (calcTypeVal === 'volume') {
            printSummaryDiv.innerHTML += `<p><strong>Ingevoerd Debiet/Massa:</strong> ${flowRateInput.value} ${flowRateUnitSelect.value}</p>`;
            if (mediumSelect.value === 'stoom' && flowRateUnitSelect.value === 'kg/h') {
                printSummaryDiv.innerHTML += `<p><strong>Ingevoerde Stoomdruk:</strong> ${steamPressureInput.value} barg</p>`;
            }
        } else {
            printSummaryDiv.innerHTML += `<p><strong>Ingevoerd Vermogen:</strong> ${powerInput.value} kW</p>`;
            if (mediumSelect.value === 'water') {
                printSummaryDiv.innerHTML += `<p><strong>Temperatuurverschil (ΔT):</strong> ${deltaTInput.value} °C</p>`;
            } else if (mediumSelect.value === 'gas') {
                printSummaryDiv.innerHTML += `<p><strong>Verbrandingswaarde:</strong> ${calorificValueInput.value} MJ/m³</p>`;
            } else if (mediumSelect.value === 'stoom') {
                printSummaryDiv.innerHTML += `<p><strong>Ingevoerde Stoomdruk:</strong> ${steamPressureInput.value} barg</p>`;
            }
        }
        printSummaryDiv.innerHTML += `<p><strong>Gekozen Stroomsnelheid:</strong> ${velocityVal} m/s</p>`;

        if (resultSectionDiv.style.display !== 'none' && resultDiameterSpan.textContent !== '--' && !isNaN(parseFloat(resultDiameterSpan.textContent))) {
            printSummaryDiv.innerHTML += `<hr>`;
            if (flowRateResultP.style.display !== 'none' && calculatedFlowRateSpan.textContent !== '--') {
                 printSummaryDiv.innerHTML += `<p><strong>Berekend Debiet:</strong> ${calculatedFlowRateSpan.textContent} m³/s</p>`;
            }
            if (massFlowRateResultP.style.display !== 'none' && calculatedMassFlowRateSpan.textContent !== '--') {
                 printSummaryDiv.innerHTML += `<p><strong>Berekend Massadebiet:</strong> ${calculatedMassFlowRateSpan.textContent} kg/s</p>`;
            }
            printSummaryDiv.innerHTML += `<p><strong>Berekende Binnendiameter: ${resultDiameterSpan.textContent} mm</strong></p>`;
        } else {
            printSummaryDiv.innerHTML += `<hr><p><strong>Geen geldig resultaat berekend of getoond.</strong></p>`;
        }

        document.body.appendChild(printSummaryDiv);
    }

    mediumSelect.addEventListener('change', updateInputVisibility);
    flowRateUnitSelect.addEventListener('change', updateInputVisibility);
    calculationTypeVolume.addEventListener('change', updateInputVisibility);
    calculationTypePower.addEventListener('change', updateInputVisibility);
    calculateButton.addEventListener('click', calculateDiameter);
    printButton.addEventListener('click', () => {
        preparePrintData();
        window.print();
    });

    updateInputVisibility();
});
