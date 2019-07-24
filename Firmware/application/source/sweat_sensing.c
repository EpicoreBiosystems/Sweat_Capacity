
#include <stdbool.h>
#include <stdint.h>
#include <math.h>
#include "nrf.h"
#include "nrf_gpiote.h"
#include "nrf_gpio.h"
#include "boards.h"
#include "nrf_drv_ppi.h"
#include "nrf_drv_timer.h"
#include "nrf_drv_gpiote.h"
#include "app_error.h"
#include "nrf_drv_spi.h"
#include "nrf_drv_saadc.h"
#include "nrf_log.h"
#include "nrf_log_ctrl.h"
#include "boards.h"
#include "sweat_sensing.h"

//#ifdef BSP_LED_0
//    #define GPIO_OUTPUT_PIN_NUMBER BSP_LED_0  /**< Pin number for output. */
//#endif
//#ifndef GPIO_OUTPUT_PIN_NUMBER
//    #error "Please indicate output pin"
//#endif

static nrf_drv_timer_t m_dac_timer = NRF_DRV_TIMER_INSTANCE(1);
static nrf_drv_timer_t waveform_period_timer = NRF_DRV_TIMER_INSTANCE(2);

void timer_dummy_handler(nrf_timer_event_t event_type, void * p_context){}

static const nrf_drv_spi_t m_dac_spi_instance = NRF_DRV_SPI_INSTANCE(0);
volatile static bool spi_tx_done = false;

static uint8_t m_dac_spi_rx_buf[2];

/*  */
nrf_ppi_channel_t ppi_channel_toggle;
nrf_ppi_channel_t ppi_channel_timer;
nrf_ppi_channel_t ppi_channel_waveform;

#define DAC_MAX_COUNT               (16384)
#define WAVEFORM_NUM_PERIODS        (20)
#define WAVEFORM_SAMPLES_PER_PERIOD (20)
#define WAVEFORM_DATA_LEN          (WAVEFORM_NUM_PERIODS * WAVEFORM_SAMPLES_PER_PERIOD)
#define BUFFER_SIZE 2
typedef struct ArrayList
{
    uint8_t buffer[BUFFER_SIZE];
} ArrayList_type;

ArrayList_type m_dac_data_list[WAVEFORM_DATA_LEN];

/* Constant and variable definitions for ADC for sweat rate and chloride measurements. */
#define SAMPLES_IN_BUFFER 200
volatile uint8_t state = 1;

static const nrf_drv_timer_t m_saadc_timer = NRF_DRV_TIMER_INSTANCE(3);
static nrf_saadc_value_t     m_buffer_pool[2][SAMPLES_IN_BUFFER];
static nrf_ppi_channel_t     m_ppi_adc_channel;
//static uint32_t              m_adc_evt_counter;

//static nrf_ppi_channel_t     m_ppi_adc_timing;
static void saadc_timer_handler(nrf_timer_event_t event_type, void * p_context)
{
}

static void spi_event_handler(nrf_drv_spi_evt_t const * p_event,
                       void *                    p_context)
{
}

static ret_code_t dac_spi_init(void)
{    
    nrf_drv_spi_config_t spi_config = NRF_DRV_SPI_DEFAULT_CONFIG;
    spi_config.frequency = NRF_DRV_SPI_FREQ_8M;
    spi_config.ss_pin   = NRF_DRV_SPI_PIN_NOT_USED;             //SPI_SS_PIN;
    spi_config.miso_pin = NRF_DRV_SPI_PIN_NOT_USED;
    spi_config.mosi_pin = SPIM0_MOSI_PIN;
    spi_config.sck_pin  = SPIM0_SCLK_PIN;
    return nrf_drv_spi_init(&m_dac_spi_instance, &spi_config, spi_event_handler, NULL);    
}

static ret_code_t dac_prepare_transfers()
{
    nrf_drv_spi_xfer_desc_t xfer = NRF_DRV_SPI_XFER_TRX(&m_dac_data_list, 2, m_dac_spi_rx_buf, 2);
    uint32_t flags = NRF_DRV_SPI_FLAG_HOLD_XFER |
                      NRF_DRV_SPI_FLAG_REPEATED_XFER | 
                       NRF_DRV_SPI_FLAG_TX_POSTINC  |
                         NRF_DRV_SPI_FLAG_NO_XFER_EVT_HANDLER;
    return (nrf_drv_spi_xfer(&m_dac_spi_instance, &xfer, flags));    
}

static void timer_dummy_handler_1(nrf_timer_event_t event_type, void * p_context)
{
//    nrf_spim_tx_buffer_set((NRF_SPIM_Type *)&m_dac_spi_instance, (uint8_t const *)&m_dac_data_list, 2);

//    nrf_gpio_pin_set(LED_2);
    dac_prepare_transfers();
//    nrf_gpio_pin_clear(LED_2);
}

static void dac_event_init()
{
    uint32_t compare_evt_addr;
    uint32_t cs_task_addr;
    uint32_t spi_end_evt_addr;
    uint32_t spi_start_task_addr;

    uint32_t waveform_count_task_addr;
//    uint32_t waveform_cc_event_addr;
//    uint32_t spi_task_stop_addr;    
//    uint32_t led_toggle_task_addr;    
//    uint32_t gpiote_task_addr;
    
    ret_code_t err_code;
    
    /* Configure timer to schecule sine waveform data trasfer to DAC for chloride measurement. */
    nrf_drv_timer_config_t timer_cfg = NRF_DRV_TIMER_DEFAULT_CONFIG;
    err_code = nrf_drv_timer_init(&m_dac_timer, &timer_cfg, timer_dummy_handler);
    APP_ERROR_CHECK(err_code);
    
    /* Configure timer in counter mode to repeat the waveform. */
    timer_cfg.mode = NRF_TIMER_MODE_COUNTER;
    err_code = nrf_drv_timer_init(&waveform_period_timer, &timer_cfg, timer_dummy_handler_1);
    APP_ERROR_CHECK(err_code);
        
//    nrf_drv_gpiote_out_config_t config_led_out = GPIOTE_CONFIG_OUT_TASK_TOGGLE(false); // start low             
    nrf_drv_gpiote_out_config_t config_cs_out = GPIOTE_CONFIG_OUT_TASK_TOGGLE(true); // Start high
    err_code = nrf_drv_gpiote_out_init(SPIM0_SS_PIN, &config_cs_out);
    APP_ERROR_CHECK(err_code);

//    nrf_drv_gpiote_out_config_t config_led_out = GPIOTE_CONFIG_OUT_TASK_TOGGLE(true); // Start high
//    err_code = nrf_drv_gpiote_out_init(LED_1, &config_led_out);
//    APP_ERROR_CHECK(err_code);
    
    err_code = nrf_drv_ppi_channel_alloc(&ppi_channel_toggle);
    APP_ERROR_CHECK(err_code);

    nrf_drv_timer_extended_compare(&m_dac_timer, 
                                   NRF_TIMER_CC_CHANNEL0, 
                                   64, 
                                   NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK, 
                                   false);

    err_code = nrf_drv_ppi_channel_alloc(&ppi_channel_timer);
    APP_ERROR_CHECK(err_code);

    compare_evt_addr = nrf_drv_timer_event_address_get(&m_dac_timer, NRF_TIMER_EVENT_COMPARE0);
    
    cs_task_addr = nrf_drv_gpiote_out_task_addr_get(SPIM0_SS_PIN);
    
    spi_start_task_addr = nrf_drv_spi_start_task_get(&m_dac_spi_instance);
    err_code = nrf_drv_ppi_channel_assign(ppi_channel_timer, compare_evt_addr, cs_task_addr);
    APP_ERROR_CHECK(err_code);
    
    err_code = nrf_drv_ppi_channel_fork_assign(ppi_channel_timer, spi_start_task_addr);
    APP_ERROR_CHECK(err_code);

    spi_end_evt_addr = nrf_drv_spi_end_event_get(&m_dac_spi_instance);

    /* Compare event after a few waveform period transmissions */
    nrf_drv_timer_extended_compare(&waveform_period_timer, 
                                   NRF_TIMER_CC_CHANNEL0, 
                                   WAVEFORM_DATA_LEN, 
                                   NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK, 
                                   true);

    waveform_count_task_addr = nrf_drv_timer_task_address_get(&waveform_period_timer, NRF_TIMER_TASK_COUNT);
//    waveform_cc_event_addr = nrf_drv_timer_event_address_get(&waveform_period_timer, NRF_TIMER_EVENT_COMPARE0);    
    
    err_code = nrf_drv_ppi_channel_assign(ppi_channel_toggle, spi_end_evt_addr, cs_task_addr);
    APP_ERROR_CHECK(err_code);
    err_code = nrf_drv_ppi_channel_fork_assign(ppi_channel_toggle, waveform_count_task_addr);
    APP_ERROR_CHECK(err_code);
    
}

void saadc_sampling_event_init(void)
{
    ret_code_t err_code;

//    /* Configure LED_2 toggle task for ADC timing measurement */
//    nrf_drv_gpiote_out_config_t config_led_out = GPIOTE_CONFIG_OUT_TASK_TOGGLE(true); // Start high
//    err_code = nrf_drv_gpiote_out_init(LED_2, &config_led_out);
//    APP_ERROR_CHECK(err_code);
//    
//    uint32_t led_toggle_task_addr = nrf_drv_gpiote_out_task_addr_get(LED_2);

    nrf_drv_timer_config_t timer_cfg = NRF_DRV_TIMER_DEFAULT_CONFIG;
    timer_cfg.bit_width = NRF_TIMER_BIT_WIDTH_32;
    err_code = nrf_drv_timer_init(&m_saadc_timer, &timer_cfg, saadc_timer_handler);
    APP_ERROR_CHECK(err_code);

    /* setup m_timer for compare event every 400ms */
//    uint32_t ticks = nrf_drv_timer_ms_to_ticks(&m_timer, 10);    
    uint32_t ticks = nrf_drv_timer_us_to_ticks(&m_saadc_timer, 6);
    nrf_drv_timer_extended_compare(&m_saadc_timer,
                                   NRF_TIMER_CC_CHANNEL0,
                                   ticks,
                                   NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK,
                                   false);
    nrf_drv_timer_enable(&m_saadc_timer);

    uint32_t timer_compare_event_addr = nrf_drv_timer_compare_event_address_get(&m_saadc_timer,
                                                                                NRF_TIMER_CC_CHANNEL0);
//    uint32_t saadc_sample_task_addr   = nrf_drv_saadc_sample_task_get();
    uint32_t saadc_sample_task_addr   = nrf_drv_saadc_sample_task_get();

    /* setup ppi channel so that timer compare event is triggering sample task in SAADC */
    err_code = nrf_drv_ppi_channel_alloc(&m_ppi_adc_channel);
    APP_ERROR_CHECK(err_code);

    err_code = nrf_drv_ppi_channel_assign(m_ppi_adc_channel,
                                          timer_compare_event_addr,
                                          saadc_sample_task_addr);    
    APP_ERROR_CHECK(err_code);
    
//    err_code = nrf_drv_ppi_channel_fork_assign(m_ppi_adc_channel, led_toggle_task_addr);
//    APP_ERROR_CHECK(err_code);
//    
//    /* Setup another PPI channel to measure the timing of SAADC conversion. */
//    uint32_t saadc_conv_end_event_addr = nrf_saadc_event_address_get(NRF_SAADC_EVENT_DONE);
//    APP_ERROR_CHECK(nrf_drv_ppi_channel_alloc(&m_ppi_adc_timing));
//    err_code = nrf_drv_ppi_channel_assign(m_ppi_adc_timing, 
//                                            saadc_conv_end_event_addr, 
//                                            led_toggle_task_addr);
//    APP_ERROR_CHECK(err_code);                                        
    
}


void saadc_sampling_event_enable(void)
{
    ret_code_t err_code = nrf_drv_ppi_channel_enable(m_ppi_adc_channel);
    APP_ERROR_CHECK(err_code);
  
//    err_code = nrf_drv_ppi_channel_enable(m_ppi_adc_timing);
//    APP_ERROR_CHECK(err_code);
//    
//    nrf_drv_gpiote_out_task_enable(LED_2);
      
}


void saadc_callback(nrf_drv_saadc_evt_t const * p_event)
{       
    if (p_event->type == NRF_DRV_SAADC_EVT_DONE)
    {
        ret_code_t err_code;

        err_code = nrf_drv_saadc_buffer_convert(p_event->data.done.p_buffer, SAMPLES_IN_BUFFER);
        APP_ERROR_CHECK(err_code);
//
//        int i;
//        NRF_LOG_INFO("ADC event number: %d", (int)m_adc_evt_counter);
//
//        for (i = 0; i < SAMPLES_IN_BUFFER; i++)
//        {
//            NRF_LOG_INFO("%d", p_event->data.done.p_buffer[i]);
//        }
//        m_adc_evt_counter++;
    }
  
//    nrf_gpio_pin_toggle(LED_3);
}


void saadc_init(void)
{
    ret_code_t err_code;
    nrf_saadc_channel_config_t chloride_channel_config =
        NRF_DRV_SAADC_DEFAULT_CHANNEL_CONFIG_SE(NRF_SAADC_INPUT_AIN2); 
    
    chloride_channel_config.acq_time = NRF_SAADC_ACQTIME_3US;
    
    err_code = nrf_drv_saadc_init(NULL, saadc_callback);
    APP_ERROR_CHECK(err_code);

    err_code = nrf_drv_saadc_channel_init(0, &chloride_channel_config);
    APP_ERROR_CHECK(err_code);

    err_code = nrf_drv_saadc_buffer_convert(m_buffer_pool[0], SAMPLES_IN_BUFFER);
    APP_ERROR_CHECK(err_code);

    err_code = nrf_drv_saadc_buffer_convert(m_buffer_pool[1], SAMPLES_IN_BUFFER);
    APP_ERROR_CHECK(err_code);

}

/**brief Function for initializing the sweat rate and chloride sensing. 
    */
void sweat_sensing_init(void)
{
    ret_code_t err_code;

    err_code = nrf_drv_ppi_init();
    APP_ERROR_CHECK(err_code);

    err_code = nrf_drv_gpiote_init();
    APP_ERROR_CHECK(err_code);

//    nrf_drv_timer_config_t timer_cfg = NRF_DRV_TIMER_DEFAULT_CONFIG;
//    err_code = nrf_drv_timer_init(&m_dac_timer, &timer_cfg, timer_dummy_handler);
//    APP_ERROR_CHECK(err_code);
//    
//    /* Configure timer in counter mode to repeat the waveform */
//    timer_cfg.mode = NRF_TIMER_MODE_COUNTER;
//    err_code = nrf_drv_timer_init(&waveform_period_timer, &timer_cfg, timer_dummy_handler_1);
//    APP_ERROR_CHECK(err_code);
//
    /* Set up an array for sine wave for chloride measurement excitation. */
    for(int i=0; i < WAVEFORM_DATA_LEN; i++)
    {
        /* Create a sine wave data array with 3.0V full-scale/1.5v mid-scale instead of 3.3v full-scale/1.65v mid-scale. */
        uint16_t sin_data_point = (uint16_t)(( 1.0 + sin(2 * PI * i / WAVEFORM_SAMPLES_PER_PERIOD)) * DAC_MAX_COUNT * (10.0 / 11.0) / 2.0);
        if(sin_data_point == DAC_MAX_COUNT) 
        {
            sin_data_point--;
        }
        m_dac_data_list[i].buffer[0] = sin_data_point >> 8;
        m_dac_data_list[i].buffer[1] = sin_data_point & 0xFF;
    }
    
    /*  Setup PPI for sine wave data transfer to DAC over SPI bus. 
        Initialization SPI interface for DAC to be used for excitation for chloride measurement. */
    err_code = dac_spi_init();
    APP_ERROR_CHECK(err_code);
            
    dac_event_init();
    dac_prepare_transfers();
    
    /* Setup ADC channels for sweat rate and chloride measurement inputs. */
    saadc_init();
    saadc_sampling_event_init();
    
//    nrf_gpio_cfg_output(LED_3);
    
}

/**@brief Start the PPI and timers for sweat rate and chloride measurement. 
*
*/
void sweat_sensing_start()
{
    ret_code_t err_code;
    
    /* Start sine wave data output to DAC over SPI. */
    nrf_drv_gpiote_out_task_enable(SPIM0_SS_PIN);
    err_code = nrf_drv_ppi_channel_enable(ppi_channel_toggle);
    APP_ERROR_CHECK(err_code);
    err_code = nrf_drv_ppi_channel_enable(ppi_channel_timer);
    APP_ERROR_CHECK(err_code);
    
    nrf_drv_timer_enable(&m_dac_timer);        
    nrf_drv_timer_enable(&waveform_period_timer);
    
//    nrf_drv_gpiote_out_task_enable(LED_1);    
    
    /* Start ADC for sweat rate and chloride measurement. */
    saadc_sampling_event_enable();
        
}



